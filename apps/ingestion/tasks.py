"""
Taches Celery de collecte (boucle ~12h, cf. brief section 2).

Chaque source alimente `normaliser_et_ecrire_bdp`, qui est le seul point
d'ecriture dans la BDP (jamais d'ecrasement : versionning parent/enfant).
Le declenchement du Matching se fait juste apres, dans `cycle_ingestion`.

Toute source logge son resultat (nb traites, erreurs) via le logger
"ingestion" — avant, les echecs reseau/parsing etaient avales en silence
(`except: continue`/`return 0`), rendant impossible de diagnostiquer une
baisse de collecte. Visible via `docker compose logs worker`.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from celery import shared_task
from django.db import IntegrityError
from django.utils import timezone

from apps.bdc.models import ActifClient
from apps.bdp.models import Renseignement
from apps.catalogue.models import ActifCatalogueProduit, ActifCatalogueVersion
from apps.matching.services import calculer_matching

logger = logging.getLogger("ingestion")

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_SEVERITE_NVD = {"CRITICAL": "critique", "HIGH": "elevee", "MEDIUM": "moyenne", "LOW": "faible"}

# CERT-FR publie deux flux JSON de meme forme : les avis (bulletins standards)
# et les alertes (urgence superieure — exploitation active ou imminente).
# Un seul coeur de collecte (_collecter_cert_fr) parametre par ces URLs.
CERT_FR_AVIS_INDEX = "https://www.cert.ssi.gouv.fr/avis/json/"
CERT_FR_AVIS_DETAIL = "https://www.cert.ssi.gouv.fr/avis/{ref}/json/"
CERT_FR_AVIS_PAGE = "https://www.cert.ssi.gouv.fr/avis/{ref}/"
CERT_FR_ALERTE_INDEX = "https://www.cert.ssi.gouv.fr/alerte/json/"
CERT_FR_ALERTE_DETAIL = "https://www.cert.ssi.gouv.fr/alerte/{ref}/json/"
CERT_FR_ALERTE_PAGE = "https://www.cert.ssi.gouv.fr/alerte/{ref}/"
CERT_FR_LOOKBACK_JOURS = 30

CNIL_RSS = "https://www.cnil.fr/fr/rss.xml"

ENDOFLIFE_INDEX = "https://endoflife.date/api/v1/products"
ENDOFLIFE_DETAIL = "https://endoflife.date/api/v1/products/{slug}"

# CISA Known Exploited Vulnerabilities : catalogue des CVE dont l'exploitation
# active est confirmee. Pas une source de nouvelles lignes — un enrichissement
# des renseignements deja connus (NVD/CERT-FR) partageant le meme CVE.
CISA_KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

_UA = {"User-Agent": "veille-saas/0.1 (POC interne, contact: matt)"}


def _get_json(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normaliser_et_ecrire_bdp(item: dict) -> Renseignement:
    """Cree ou met a jour (par nouvelle version) un Renseignement a partir
    d'un item normalise {type, titre, description, source, reference_externe,
    criticite, taxonomie_*, decouvert_le}.
    """
    existant = (
        Renseignement.objects.filter(
            source=item["source"], reference_externe=item.get("reference_externe", "")
        )
        .order_by("-decouvert_le")
        .first()
    )

    a_change = existant is None or _contenu_modifie(existant, item)
    if not a_change:
        return existant

    try:
        return Renseignement.objects.create(
            parent=existant,
            type=item["type"],
            titre=item["titre"],
            description=item["description"],
            source=item["source"],
            url_source=item.get("url_source", ""),
            reference_externe=item.get("reference_externe", ""),
            criticite=item.get("criticite", ""),
            nature=item.get("nature", ""),
            taxonomie_categorie=item.get("taxonomie_categorie", ""),
            taxonomie_editeur=item.get("taxonomie_editeur", ""),
            taxonomie_produit=item.get("taxonomie_produit", ""),
            taxonomie_version=item.get("taxonomie_version", ""),
            taxonomie_referentiel=item.get("taxonomie_referentiel", ""),
            decouvert_le=item["decouvert_le"],
            cvss_score=item.get("cvss_score"),
            cvss_vector=item.get("cvss_vector", ""),
        )
    except IntegrityError:
        # Course avec un autre run (cycle planifie + declenchement manuel
        # simultanes, par ex.) : quelqu'un a deja ecrit EXACTEMENT cette
        # revision (source + reference_externe + decouvert_le, contrainte
        # unique) entre notre lecture et notre ecriture. On relit plutot que
        # de planter tout le cycle — c'est le garde-fou base evoque par le
        # client ("pas de doublon"), la verification applicative ci-dessus
        # n'etant pas atomique a elle seule.
        logger.info(
            "Doublon evite en base (source=%s, ref=%s) : deja ecrit par un autre run.",
            item["source"], item.get("reference_externe", ""),
        )
        return Renseignement.objects.filter(
            source=item["source"],
            reference_externe=item.get("reference_externe", ""),
            decouvert_le=item["decouvert_le"],
        ).first()


def _contenu_modifie(existant: Renseignement, item: dict) -> bool:
    return existant.description != item["description"] or existant.criticite != item.get(
        "criticite", ""
    )


def _resume(texte: str, n: int = 100) -> str:
    """Premiere phrase (ou premiers n caracteres) d'un texte long, pour un
    titre court — la reference (CVE/CERTFR-ID) est deja affichee separement
    par les gabarits via `reference_courte`, jamais repetee dans le titre."""
    texte = (texte or "").strip()
    if not texte:
        return ""
    fin = texte.find(". ")
    if 0 < fin < n:
        return texte[:fin].strip()
    return texte[:n].rstrip() + ("…" if len(texte) > n else "")


def _nvd_description(cve: dict) -> str:
    for d in cve.get("descriptions", []):
        if d.get("lang") == "en":
            return d.get("value", "")
    return ""


def _nvd_severite(cve: dict) -> str:
    metrics = cve.get("metrics", {})
    for cle in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for entree in metrics.get(cle, []):
            sev = entree.get("baseSeverity") or entree.get("cvssData", {}).get("baseSeverity")
            if sev:
                return _SEVERITE_NVD.get(sev.upper(), "moyenne")
    return "moyenne"


def _nvd_cvss(cve: dict):
    """Retourne (score, vecteur_brut) depuis la premiere metrique CVSS
    disponible (v3.1 en priorite), pour l'analyse d'exploitabilite/impact."""
    metrics = cve.get("metrics", {})
    for cle in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for entree in metrics.get(cle, []):
            data = entree.get("cvssData", {})
            vecteur = data.get("vectorString")
            score = data.get("baseScore")
            if vecteur:
                return score, vecteur
    return None, ""


@shared_task
def collecter_nvd_cve():
    """Interroge l'API publique NVD (CVE 2.0) pour chaque actif technique
    declare par le client, normalise les resultats dans la BDP.

    Sans cle API, NVD limite a ~5 requetes / 30s : on espace les appels.
    Une erreur reseau sur un actif ne doit pas interrompre les autres.
    """
    actifs = list(ActifClient.objects.filter(type="technique").exclude(produit=""))
    total = 0
    erreurs = 0

    for i, actif in enumerate(actifs):
        if i:
            time.sleep(6)

        params = urllib.parse.urlencode({"keywordSearch": actif.produit, "resultsPerPage": 5})
        req = urllib.request.Request(f"{NVD_API}?{params}", headers=_UA)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            erreurs += 1
            logger.warning("NVD %s: echec requete (%s)", actif.produit, exc)
            continue

        for vuln in payload.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id")
            if not cve_id:
                continue
            try:
                publie = datetime.fromisoformat(cve["published"])
            except (KeyError, ValueError):
                publie = timezone.now()
            if timezone.is_naive(publie):
                publie = timezone.make_aware(publie, timezone.get_default_timezone())

            score, vecteur = _nvd_cvss(cve)
            description = _nvd_description(cve)[:2000] or "(pas de description disponible)"
            normaliser_et_ecrire_bdp({
                "type": "technique",
                "titre": f"{actif.produit} — {_resume(description)}",
                "description": description,
                "source": "NVD",
                "url_source": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                "reference_externe": cve_id,
                "criticite": _nvd_severite(cve),
                "nature": "vulnerabilite",
                "taxonomie_editeur": actif.editeur,
                "taxonomie_produit": actif.produit,
                "taxonomie_version": actif.version,
                "decouvert_le": publie,
                "cvss_score": score,
                "cvss_vector": vecteur,
            })
            total += 1

    logger.info("NVD: %d renseignements traites sur %d actifs (%d en erreur)", total, len(actifs), erreurs)
    return total


@shared_task
def enrichir_kev():
    """Enrichit les renseignements deja connus (typiquement NVD, parfois
    CERT-FR) avec le statut CISA KEV : ce catalogue liste les CVE dont
    l'exploitation active est confirmee, un signal de priorite fort qu'une
    simple note CVSS ne donne pas. N'ecrit JAMAIS de nouvelle ligne — pure
    mise a jour des champs d'enrichissement (tags, niveau_confiance,
    cve_associees) sur les Renseignement existants dont `reference_externe`
    correspond au CVE.
    """
    try:
        payload = _get_json(CISA_KEV)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("KEV: echec recuperation catalogue (%s)", exc)
        return 0

    total = 0
    for vuln in payload.get("vulnerabilities", []):
        cve_id = vuln.get("cveID")
        if not cve_id:
            continue

        for r in Renseignement.objects.filter(reference_externe=cve_id):
            change = False
            if "KEV" not in r.tags:
                r.tags = [*r.tags, "KEV"]
                change = True
            if cve_id not in r.cve_associees:
                r.cve_associees = [*r.cve_associees, cve_id]
                change = True
            if r.niveau_confiance != "eleve":
                r.niveau_confiance = "eleve"
                change = True
            if change:
                r.save(update_fields=["tags", "cve_associees", "niveau_confiance"])
                total += 1

    logger.info(
        "KEV: %d renseignements enrichis (catalogue de %d CVE exploitees)",
        total, payload.get("count", 0),
    )
    return total


def _certfr_criticite(risks: list) -> str:
    """CERT-FR ne fournit pas de score CVSS par avis (contrairement a NVD) :
    on deduit une criticite indicative a partir du PREMIER risque declare
    par l'avis (CERT-FR liste les impacts par ordre de gravite decroissante :
    se baser sur l'ensemble de la liste ferait passer "critique" la quasi-
    totalite des avis multi-CVE, qui listent presque toujours l'execution de
    code arbitraire parmi 5-6 impacts possibles meme quand ce n'est pas le
    plus probable pour l'ensemble des CVE couverts)."""
    if not risks:
        return "faible"
    texte = risks[0].get("description", "").lower()
    if "code arbitraire" in texte:
        return "critique"
    if "élévation de privilèges" in texte or "contournement" in texte:
        return "elevee"
    if "déni de service" in texte or "confidentialité" in texte or "intégrité" in texte:
        return "moyenne"
    return "faible"


def _collecter_cert_fr(*, index_url: str, detail_tpl: str, page_tpl: str, label: str, lookback_jours: int):
    """Coeur partage entre `collecter_cert_fr_avis` et
    `collecter_cert_fr_alertes` — meme format JSON cote CERT-FR pour les deux
    flux, seules les URLs (et donc la nature avis/alerte) changent.

    Un avis/alerte peut couvrir plusieurs produits/editeurs
    (`affected_systems`) : on cree un Renseignement par couple editeur+produit
    distinct pour que le Matching (exact editeur+produit) puisse s'appliquer,
    exactement comme pour un CVE NVD.

    Fenetre glissante de `lookback_jours` sur la date de derniere revision,
    pour eviter de reparcourir en detail tout l'historique CERT-FR a chaque
    cycle ; un avis/alerte deja connu et non revise depuis n'est pas
    retelecharge.
    """
    try:
        index = _get_json(index_url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("%s: echec recuperation index (%s)", label, exc)
        return 0

    seuil = timezone.now() - timedelta(days=lookback_jours)
    total = 0
    erreurs = 0

    for entree in index:
        ref = entree.get("reference")
        if not ref:
            continue
        try:
            revision = datetime.fromisoformat(entree["last_revision_date"])
        except (KeyError, ValueError):
            continue
        if timezone.is_naive(revision):
            revision = timezone.make_aware(revision, timezone.get_default_timezone())
        if revision < seuil:
            continue

        plus_recent_connu = (
            Renseignement.objects.filter(source="CERT-FR", reference_externe__startswith=ref)
            .order_by("-decouvert_le")
            .first()
        )
        if plus_recent_connu and plus_recent_connu.decouvert_le >= revision:
            continue

        time.sleep(0.3)
        try:
            detail = _get_json(detail_tpl.format(ref=ref))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            erreurs += 1
            logger.warning("%s %s: echec recuperation detail (%s)", label, ref, exc)
            continue

        criticite = _certfr_criticite(detail.get("risks", []))
        url_avis = page_tpl.format(ref=ref)
        titre_avis = detail.get("title", "")
        description = (detail.get("summary") or titre_avis or "")[:2000] or (
            "(pas de description disponible)"
        )

        produits_vus = set()
        for systeme in detail.get("affected_systems", []):
            produit_data = systeme.get("product", {})
            nom_produit = produit_data.get("name", "")
            nom_editeur = produit_data.get("vendor", {}).get("name", "")
            if not nom_produit or not nom_editeur or (nom_editeur, nom_produit) in produits_vus:
                continue
            produits_vus.add((nom_editeur, nom_produit))

            normaliser_et_ecrire_bdp({
                "type": "technique",
                "titre": f"{nom_produit} — {titre_avis}" if titre_avis else nom_produit,
                "description": description,
                "source": "CERT-FR",
                "url_source": url_avis,
                "reference_externe": f"{ref}::{nom_produit}",
                "criticite": criticite,
                "nature": "vulnerabilite",
                "taxonomie_editeur": nom_editeur,
                "taxonomie_produit": nom_produit,
                "decouvert_le": revision,
            })
            total += 1

        if not produits_vus:
            # Avis/alerte sans produit structure (rare) : conserve quand meme,
            # visible dans Actualites, simplement non matche a un actif.
            normaliser_et_ecrire_bdp({
                "type": "technique",
                "titre": titre_avis or ref,
                "description": description,
                "source": "CERT-FR",
                "url_source": url_avis,
                "reference_externe": ref,
                "criticite": criticite,
                "nature": "vulnerabilite",
                "decouvert_le": revision,
            })
            total += 1

    logger.info("%s: %d renseignements traites (%d erreurs de detail)", label, total, erreurs)
    return total


@shared_task
def collecter_cert_fr_avis(lookback_jours: int = CERT_FR_LOOKBACK_JOURS):
    """Avis CERT-FR — bulletins de securite standards."""
    return _collecter_cert_fr(
        index_url=CERT_FR_AVIS_INDEX,
        detail_tpl=CERT_FR_AVIS_DETAIL,
        page_tpl=CERT_FR_AVIS_PAGE,
        label="CERT-FR avis",
        lookback_jours=lookback_jours,
    )


@shared_task
def collecter_cert_fr_alertes(lookback_jours: int = CERT_FR_LOOKBACK_JOURS):
    """Alertes CERT-FR — urgence superieure a un avis standard (exploitation
    active ou imminente signalee par l'ANSSI). Meme mecanique de collecte que
    les avis, cf. `_collecter_cert_fr`."""
    return _collecter_cert_fr(
        index_url=CERT_FR_ALERTE_INDEX,
        detail_tpl=CERT_FR_ALERTE_DETAIL,
        page_tpl=CERT_FR_ALERTE_PAGE,
        label="CERT-FR alerte",
        lookback_jours=lookback_jours,
    )


def _parser_rss(payload: bytes) -> list[dict]:
    """Parseur RSS 2.0 minimal (stdlib uniquement)."""
    root = ET.fromstring(payload)
    items = []
    for item in root.iter("item"):
        lien = (item.findtext("link") or "").strip()
        titre = (item.findtext("title") or "").strip()
        if not titre or not lien:
            continue
        items.append({
            "titre": titre,
            "lien": lien,
            "description": (item.findtext("description") or "").strip(),
            "pub_date": (item.findtext("pubDate") or "").strip(),
            "guid": (item.findtext("guid") or lien).strip(),
        })
    return items


def _parser_date_rss(texte: str):
    try:
        dt = parsedate_to_datetime(texte)
    except (TypeError, ValueError):
        return timezone.now()
    if dt is None:
        return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


@shared_task
def collecter_referentiels_normatifs():
    """Collecte reelle des actualites de la CNIL (regulateur RGPD francais),
    taguees `taxonomie_referentiel="RGPD"` pour le Matching.

    Limite connue, verifiee a nouveau lors de cette revision : il n'existe
    toujours pas de flux public structure et gratuit equivalent pour
    NIS2 / ISO 27001 / DORA (ISO est payant ; NIS2/DORA sont du texte legal
    EUR-Lex/Legifrance sans flux exploitable simplement sans inscription
    developpeur — portail PISTE pour Legifrance). A specifier au cas par cas
    si le client veut aller plus loin sur ces referentiels."""
    try:
        req = urllib.request.Request(CNIL_RSS, headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("CNIL: echec recuperation flux (%s)", exc)
        return 0

    try:
        items = _parser_rss(payload)
    except ET.ParseError as exc:
        logger.warning("CNIL: echec parsing RSS (%s)", exc)
        return 0

    total = 0
    for item in items:
        normaliser_et_ecrire_bdp({
            "type": "normatif",
            "titre": item["titre"],
            "description": item["description"][:2000] or "(pas de description disponible)",
            "source": "CNIL",
            "url_source": item["lien"],
            "reference_externe": item["guid"],
            "criticite": "faible",
            "nature": "information",
            "taxonomie_referentiel": "RGPD",
            "decouvert_le": _parser_date_rss(item["pub_date"]),
        })
        total += 1

    logger.info("CNIL: %d renseignements normatifs traites", total)
    return total


# ---- Catalogue d'actifs (categorie > editeur > produit > versions) --------
# endoflife.date : ~470 produits reels (OS, bases de donnees, langages,
# frameworks, et meme des appliances reseau comme PAN-OS/FortiOS), avec leurs
# versions et leur etat de maintenance — bien plus solide qu'une liste tapee
# a la main, et assez petit (~470 produits) pour etre rafraichi entierement
# a chaque cycle sans mecanisme d'incrementalite complexe.

_CATEGORIE_ENDOFLIFE = {
    "os": "Système d'exploitation",
    "lang": "Langage / runtime",
    "database": "Base de données",
    "server-app": "Applicatif serveur",
    "framework": "Framework",
    "app": "Application",
    "service": "Service cloud",
    "device": "Matériel / appliance",
    "standard": "Standard",
}
# Certains editeurs reseau/securite sont classes "os" par endoflife.date (ex:
# PAN-OS, FortiOS) — on les regroupe a part, plus parlant pour un client ESN
# que de les noyer dans "Systeme d'exploitation" a cote de Debian/Windows.
_TAGS_PARE_FEU = {"palo-alto-networks", "fortinet", "stormshield", "cisco", "checkpoint", "sonicwall", "watchguard", "juniper"}

_EDITEURS_CONNUS = {
    "microsoft": "Microsoft", "debian": "Debian Project", "canonical": "Canonical",
    "redhat": "Red Hat", "fortinet": "Fortinet", "paloaltonetworks": "Palo Alto Networks",
    "cisco": "Cisco", "stormshield": "Stormshield", "oracle": "Oracle",
    "apache": "Apache Software Foundation", "mongodb": "MongoDB Inc.",
    "postgresql": "PostgreSQL Global Development Group", "python": "Python Software Foundation",
    "nodejs": "Node.js Foundation", "docker": "Docker Inc.", "vmware": "VMware",
    "google": "Google", "amazon": "Amazon", "ibm": "IBM", "suse": "SUSE",
    "almalinux": "AlmaLinux OS Foundation", "rocky": "Rocky Linux Foundation",
    "mysql": "Oracle", "elastic": "Elastic", "hashicorp": "HashiCorp",
    "kubernetes": "Cloud Native Computing Foundation", "gitlab": "GitLab Inc.",
    "atlassian": "Atlassian", "wordpress": "WordPress Foundation",
}


def _humaniser_editeur(slug: str) -> str:
    if not slug:
        return "Éditeur non précisé"
    cle = slug.lower().replace("-", "").replace("_", "")
    if cle in _EDITEURS_CONNUS:
        return _EDITEURS_CONNUS[cle]
    return slug.replace("-", " ").replace("_", " ").title()


def _vendor_depuis_cpe(identifiers: list) -> str:
    """Extrait le segment 'vendor' d'un identifiant CPE 2.3 ou 2.2."""
    for ident in identifiers:
        if ident.get("type") != "cpe":
            continue
        id_ = ident.get("id", "")
        if id_.startswith("cpe:2.3:"):
            parts = id_.split(":")
            if len(parts) > 3:
                return parts[3]
        elif id_.startswith("cpe:/"):
            parts = id_[len("cpe:/"):].split(":")
            if len(parts) > 1:
                return parts[1]
    return ""


def _categorie_produit(categorie_endoflife: str, tags: list) -> str:
    if any(t in _TAGS_PARE_FEU for t in tags):
        return "Pare-feu / Réseau"
    return _CATEGORIE_ENDOFLIFE.get(categorie_endoflife, "Autre")


def _parser_date_iso(texte):
    if not texte:
        return None
    try:
        return datetime.strptime(texte, "%Y-%m-%d").date()
    except ValueError:
        return None


@shared_task
def collecter_catalogue_actifs():
    """Peuple le catalogue de reference des actifs declarables depuis
    endoflife.date (~470 produits : OS, bases de donnees, langages,
    frameworks, appliances reseau connues, avec leurs versions et leur etat
    de maintenance). Objectif : le client trouve toujours son actif quand il
    le cherche, au lieu de dependre d'une liste figee tapee a la main."""
    try:
        index = _get_json(ENDOFLIFE_INDEX)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("endoflife.date: echec recuperation index (%s)", exc)
        return {"produits": 0, "versions": 0}

    total_produits = 0
    total_versions = 0
    erreurs = 0

    for entree in index.get("result", []):
        slug = entree.get("name")
        if not slug:
            continue

        time.sleep(0.15)
        try:
            detail = _get_json(ENDOFLIFE_DETAIL.format(slug=slug)).get("result", {})
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            erreurs += 1
            logger.warning("endoflife.date %s: echec recuperation detail (%s)", slug, exc)
            continue

        vendor_slug = _vendor_depuis_cpe(detail.get("identifiers", []))
        editeur = _humaniser_editeur(vendor_slug or slug)
        categorie = _categorie_produit(entree.get("category", ""), entree.get("tags", []))
        produit_nom = detail.get("label") or entree.get("label") or slug

        produit, _created = ActifCatalogueProduit.objects.update_or_create(
            categorie=categorie, editeur=editeur, produit=produit_nom,
            defaults={"source": "endoflife", "identifiant_source": slug},
        )
        total_produits += 1

        versions_vues = set()
        for release in detail.get("releases", []):
            version = (release.get("latest") or {}).get("name") or release.get("name")
            if not version or version in versions_vues:
                continue
            versions_vues.add(version)
            ActifCatalogueVersion.objects.update_or_create(
                produit=produit, version=version,
                defaults={
                    "label": release.get("label", ""),
                    "maintenue": bool(release.get("isMaintained", True)),
                    "sortie_le": _parser_date_iso(release.get("releaseDate")),
                },
            )
            total_versions += 1

    logger.info(
        "endoflife.date: %d produits, %d versions (%d produits en erreur)",
        total_produits, total_versions, erreurs,
    )
    return {"produits": total_produits, "versions": total_versions}


@shared_task
def cycle_ingestion():
    """Orchestre un cycle complet de collecte puis declenche le Matching."""
    logger.info("=== Debut du cycle d'ingestion ===")
    collecter_nvd_cve()
    enrichir_kev()
    collecter_cert_fr_avis()
    collecter_cert_fr_alertes()
    collecter_referentiels_normatifs()
    collecter_catalogue_actifs()
    calculer_matching()
    logger.info("=== Fin du cycle d'ingestion ===")
