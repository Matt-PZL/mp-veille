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
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from celery import shared_task
from django.db import IntegrityError
from django.db.models import Max
from django.utils import timezone

from apps.bdp.models import Renseignement
from apps.catalogue.models import ActifCatalogueProduit, ActifCatalogueVersion
from apps.matching.services import calculer_matching

logger = logging.getLogger("ingestion")

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.environ.get("NVD_API_KEY", "")
_SEVERITE_NVD = {"CRITICAL": "critique", "HIGH": "elevee", "MEDIUM": "moyenne", "LOW": "faible"}
_BACKFILL_JOURS = 365  # premier run de chaque source proactive (cf. module docstring)
_NVD_FENETRE_MAX_JOURS = 120  # limite imposee par l'API NVD par requete

DEBIAN_TRACKER = "https://security-tracker.debian.org/tracker/data/json"

UBUNTU_USN = "https://ubuntu.com/security/notices.json"

GITHUB_ADVISORIES = "https://api.github.com/advisories"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_GHSA_BACKFILL_JOURS_SANS_TOKEN = 90  # 60 req/h sans token : 365j prendrait des heures
_GHSA_BACKFILL_JOURS_AVEC_TOKEN = _BACKFILL_JOURS  # 5000 req/h avec token

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


def _nvd_headers():
    h = dict(_UA)
    if NVD_API_KEY:
        h["apiKey"] = NVD_API_KEY
    return h


def _cpe_vendor_produit(cve: dict) -> tuple[str, str]:
    """Vendor/produit du premier CPE affecte trouve dans les configurations
    NVD (structure CPE 2.3 brute — differente du catalogue endoflife.date,
    qui a sa propre `_vendor_depuis_cpe` pour un format different)."""
    for config in cve.get("configurations", []):
        for node in config.get("nodes", []):
            for match in node.get("cpeMatch", []):
                if not match.get("vulnerable", True):
                    continue
                criteria = match.get("criteria", "")
                parts = criteria.split(":")
                if criteria.startswith("cpe:2.3:") and len(parts) > 4:
                    vendor, produit = parts[3], parts[4]
                    if vendor not in ("", "*") and produit not in ("", "*"):
                        return _humaniser_editeur(vendor), produit.replace("_", " ").replace("-", " ").title()
    return "", ""


@shared_task
def collecter_nvd_cve():
    """Interroge l'API publique NVD (CVE 2.0) de facon PROACTIVE, sur une
    fenetre de dates de publication — plus aucune dependance a la BDC
    (ActifClient) : la BDP doit rester une base de renseignements autonome,
    c'est le Matching qui la relie ensuite au perimetre d'un client, jamais
    l'ingestion elle-meme (cf. module docstring).

    Fenetre determinee par ce qui est deja en base pour cette source : premier
    run = backfill sur `_BACKFILL_JOURS` (365j), runs suivants = uniquement
    les nouveautes depuis la derniere collecte — meme principe que
    `_collecter_cert_fr`. Decoupee en tranches de `_NVD_FENETRE_MAX_JOURS`
    (limite NVD par requete), chaque tranche paginee par `resultsPerPage`.

    Sans cle API, NVD limite a ~5 requetes/30s. Avec NVD_API_KEY (var d'env,
    gratuite et immediate sur nvd.nist.gov/developers/request-an-api-key),
    50/30s. Une erreur reseau sur une tranche ne doit pas interrompre les
    autres.
    """
    # Borne toujours a _BACKFILL_JOURS, meme si une ligne NVD plus ancienne
    # traine deja en base (ex : d'anciennes entrees reactives, avant cette
    # bascule proactive, sans limite de date) : sans ce plancher, un `derniere`
    # ancien ferait remonter `depuis` bien avant la fenetre voulue — bug reel
    # trouve pendant la verification (est reparti chercher des CVE de 2005).
    plancher = timezone.now() - timedelta(days=_BACKFILL_JOURS)
    derniere = Renseignement.objects.filter(source="NVD").aggregate(m=Max("decouvert_le"))["m"]
    depuis = max(derniere, plancher) if derniere else plancher
    jusqua = timezone.now()

    total = 0
    erreurs = 0
    premiere_requete = True
    debut_tranche = depuis

    while debut_tranche < jusqua:
        fin_tranche = min(debut_tranche + timedelta(days=_NVD_FENETRE_MAX_JOURS), jusqua)
        start_index = 0

        while True:
            if not premiere_requete:
                time.sleep(0.7 if NVD_API_KEY else 6.5)
            premiere_requete = False

            params = urllib.parse.urlencode({
                "pubStartDate": debut_tranche.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "pubEndDate": fin_tranche.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "resultsPerPage": 2000,
                "startIndex": start_index,
            })
            req = urllib.request.Request(f"{NVD_API}?{params}", headers=_nvd_headers())
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = json.load(resp)
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                erreurs += 1
                logger.warning(
                    "NVD %s -> %s (index %d): echec requete (%s)",
                    debut_tranche.date(), fin_tranche.date(), start_index, exc,
                )
                break

            vulns = payload.get("vulnerabilities", [])
            for vuln in vulns:
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

                editeur, produit = _cpe_vendor_produit(cve)
                score, vecteur = _nvd_cvss(cve)
                description = _nvd_description(cve)[:2000] or "(pas de description disponible)"
                normaliser_et_ecrire_bdp({
                    "type": "technique",
                    "titre": f"{produit or cve_id} — {_resume(description)}",
                    "description": description,
                    "source": "NVD",
                    "url_source": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "reference_externe": cve_id,
                    "criticite": _nvd_severite(cve),
                    "nature": "vulnerabilite",
                    "taxonomie_editeur": editeur,
                    "taxonomie_produit": produit,
                    "decouvert_le": publie,
                    "cvss_score": score,
                    "cvss_vector": vecteur,
                })
                total += 1

            start_index += len(vulns)
            if not vulns or start_index >= payload.get("totalResults", 0):
                break

        logger.info("NVD: tranche %s -> %s terminee, %d CVE cumules", debut_tranche.date(), fin_tranche.date(), total)
        debut_tranche = fin_tranche

    logger.info(
        "NVD: %d CVE traites (%d tranches en erreur), fenetre %s -> %s",
        total, erreurs, depuis.date(), jusqua.date(),
    )
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
def collecter_debian_security():
    """Debian Security Tracker : CVE par paquet Debian, avec statut par
    version de la distro (open/resolved). Comme les autres sources
    proactives, parcourt TOUT le tracker (~4000 paquets), sans regarder la
    BDC — c'est exactement ce qui manquait pour des paquets comme OpenSSH,
    jamais cherches par l'ancienne version reactive de la collecte NVD.

    Ne retient que les CVE encore ouvertes sur au moins une version : le
    tracker ne porte aucune date par entree (limite du format, documentee
    ici plutot que devinee), filtrer par statut est le seul levier
    disponible pour rester pertinent plutot que de remonter 25 ans
    d'historique clos.
    """
    try:
        catalogue = _get_json(DEBIAN_TRACKER)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Debian Security Tracker: echec recuperation (%s)", exc)
        return 0

    total = 0
    for paquet, cves in catalogue.items():
        for cve_id, info in cves.items():
            releases = info.get("releases", {})
            if not any(r.get("status") == "open" for r in releases.values()):
                continue

            # Cle composite CVE::paquet : une meme CVE touche parfois plusieurs
            # paquets Debian (ex : une lib partagee) — une cle nue aurait
            # collabe ces occurrences sur une seule ligne et perdu le
            # rattachement produit pour tous les paquets sauf le premier
            # rencontre (bug reel trouve et corrige pendant la verification).
            ref = f"{cve_id}::{paquet}"

            # Pas de date fiable dans la source : on reutilise celle deja en
            # base si cette entree est deja connue (pour que le
            # dedoublonnage de normaliser_et_ecrire_bdp la retrouve), sinon
            # "maintenant" pour une premiere ecriture.
            existant = (
                Renseignement.objects.filter(source="Debian Security Tracker", reference_externe=ref)
                .order_by("-decouvert_le")
                .first()
            )
            decouvert_le = existant.decouvert_le if existant else timezone.now()

            description = (info.get("description") or "")[:2000] or "(pas de description disponible)"
            normaliser_et_ecrire_bdp({
                "type": "technique",
                "titre": f"{paquet} — {_resume(description)}" if description else paquet,
                "description": description,
                "source": "Debian Security Tracker",
                "url_source": f"https://security-tracker.debian.org/tracker/{cve_id}",
                "reference_externe": ref,
                "criticite": "moyenne",  # pas de score dans la source, urgence textuelle heterogene par release
                "nature": "vulnerabilite",
                "taxonomie_editeur": "Debian",
                "taxonomie_produit": paquet,
                "decouvert_le": decouvert_le,
            })
            total += 1

    logger.info("Debian Security Tracker: %d renseignements traites (CVE encore ouvertes)", total)
    return total


@shared_task
def collecter_ubuntu_usn():
    """Ubuntu Security Notices (USN) — complement direct de Debian Security
    Tracker pour les actifs Ubuntu specifiquement. Meme principe de fenetre
    proactive que NVD : backfill `_BACKFILL_JOURS` au premier run, puis
    uniquement les nouveautes depuis la derniere collecte."""
    # Meme plancher defensif que NVD (cf. son commentaire) : ne jamais
    # redescendre sous _BACKFILL_JOURS meme si une ligne plus ancienne existe.
    plancher = timezone.now() - timedelta(days=_BACKFILL_JOURS)
    derniere = Renseignement.objects.filter(source="Ubuntu USN").aggregate(m=Max("decouvert_le"))["m"]
    seuil = max(derniere, plancher) if derniere else plancher

    total = 0
    erreurs = 0
    offset = 0
    LIMITE_PAGE = 20  # max autorise par l'API (422 au-dela, verifie en direct)

    while True:
        params = urllib.parse.urlencode({"limit": LIMITE_PAGE, "offset": offset})
        try:
            payload = _get_json(f"{UBUNTU_USN}?{params}")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            erreurs += 1
            logger.warning("Ubuntu USN: echec recuperation page offset=%d (%s)", offset, exc)
            break

        notices = payload.get("notices", [])
        if not notices:
            break

        arret = False
        for notice in notices:
            try:
                publie = datetime.fromisoformat(notice["published"])
            except (KeyError, ValueError):
                continue
            if timezone.is_naive(publie):
                publie = timezone.make_aware(publie, timezone.get_default_timezone())
            if publie < seuil:
                arret = True
                break

            usn_id = notice.get("id", "")
            titre = notice.get("title", "")
            description = (notice.get("description") or notice.get("summary") or "")[:2000] or (
                "(pas de description disponible)"
            )

            paquets_vus = set()
            for paquets in notice.get("release_packages", {}).values():
                for p in paquets:
                    nom = p.get("name", "")
                    if not nom or nom in paquets_vus:
                        continue
                    paquets_vus.add(nom)
                    normaliser_et_ecrire_bdp({
                        "type": "technique",
                        "titre": f"{nom} — {titre}" if titre else nom,
                        "description": description,
                        "source": "Ubuntu USN",
                        "url_source": f"https://ubuntu.com/security/notices/{usn_id}",
                        "reference_externe": f"{usn_id}::{nom}",
                        "criticite": "moyenne",
                        "nature": "vulnerabilite",
                        "taxonomie_editeur": "Canonical",
                        "taxonomie_produit": nom,
                        "decouvert_le": publie,
                    })
                    total += 1

        if arret:
            break
        offset += LIMITE_PAGE
        time.sleep(0.2)

    logger.info("Ubuntu USN: %d renseignements traites (%d erreurs)", total, erreurs)
    return total


def _github_headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": _UA["User-Agent"]}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _lien_suivant(entete_link: str | None) -> str | None:
    """Extrait l'URL rel="next" d'un en-tete HTTP Link (pagination par
    curseur de l'API GitHub — pas d'offset/page classique)."""
    if not entete_link:
        return None
    for morceau in entete_link.split(","):
        if 'rel="next"' in morceau:
            m = re.search(r"<([^>]+)>", morceau)
            if m:
                return m.group(1)
    return None


@shared_task
def collecter_github_advisories():
    """GitHub Security Advisories : couvre l'ecosysteme open-source (pip,
    npm, Maven, Go, RubyGems...) largement hors radar CERT-FR/NVD/Debian.

    60 requetes/heure sans authentification, 5000/h avec GITHUB_TOKEN (var
    d'env, token gratuit sans permission particuliere) : backfill limite a
    90 jours sans token, `_BACKFILL_JOURS` (365) avec. Pagination par
    curseur (en-tete Link) ; la liste est deja triee par date de publication
    decroissante donc pas besoin de fenetre de dates cote requete — on
    s'arrete des qu'on sort de la fenetre ou qu'on retrouve un ghsa_id deja
    connu."""
    profondeur = _GHSA_BACKFILL_JOURS_AVEC_TOKEN if GITHUB_TOKEN else _GHSA_BACKFILL_JOURS_SANS_TOKEN
    seuil = timezone.now() - timedelta(days=profondeur)

    total = 0
    erreurs = 0
    url = f"{GITHUB_ADVISORIES}?per_page=100&sort=published&direction=desc"

    while url:
        req = urllib.request.Request(url, headers=_github_headers())
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                lien_suivant = _lien_suivant(resp.headers.get("Link"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            erreurs += 1
            logger.warning("GitHub Advisories: echec requete (%s)", exc)
            break

        arret = False
        for advisory in payload:
            ghsa_id = advisory.get("ghsa_id")
            if not ghsa_id:
                continue
            try:
                publie = datetime.fromisoformat((advisory.get("published_at") or "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if publie < seuil:
                arret = True
                break
            if Renseignement.objects.filter(
                source="GitHub Advisories", reference_externe__startswith=ghsa_id
            ).exists():
                arret = True
                break

            severite = (advisory.get("severity") or "").upper()
            cvss = (advisory.get("cvss_severities") or {}).get("cvss_v3") or {}
            description = (advisory.get("summary") or advisory.get("description") or "")[:2000] or (
                "(pas de description disponible)"
            )

            paquets_vus = set()
            for vuln in advisory.get("vulnerabilities", []):
                pkg = vuln.get("package") or {}
                nom = pkg.get("name", "")
                ecosysteme = pkg.get("ecosystem", "")
                if not nom or nom in paquets_vus:
                    continue
                paquets_vus.add(nom)
                normaliser_et_ecrire_bdp({
                    "type": "technique",
                    "titre": f"{nom} — {advisory.get('summary', '')}"[:500],
                    "description": description,
                    "source": "GitHub Advisories",
                    "url_source": advisory.get("html_url", ""),
                    "reference_externe": f"{ghsa_id}::{nom}",
                    "criticite": _SEVERITE_NVD.get(severite, "moyenne"),
                    "nature": "vulnerabilite",
                    "taxonomie_categorie": ecosysteme,
                    "taxonomie_produit": nom,
                    "decouvert_le": publie,
                    "cvss_score": cvss.get("score") or None,
                    "cvss_vector": cvss.get("vector_string") or "",
                })
                total += 1

            if not paquets_vus:
                normaliser_et_ecrire_bdp({
                    "type": "technique",
                    "titre": (advisory.get("summary") or ghsa_id)[:500],
                    "description": description,
                    "source": "GitHub Advisories",
                    "url_source": advisory.get("html_url", ""),
                    "reference_externe": ghsa_id,
                    "criticite": _SEVERITE_NVD.get(severite, "moyenne"),
                    "nature": "vulnerabilite",
                    "decouvert_le": publie,
                    "cvss_score": cvss.get("score") or None,
                    "cvss_vector": cvss.get("vector_string") or "",
                })
                total += 1

        if arret:
            break
        url = lien_suivant
        if url:
            time.sleep(0.1 if GITHUB_TOKEN else 1.2)

    logger.info(
        "GitHub Advisories: %d renseignements traites (%d erreurs, profondeur %d jours)",
        total, erreurs, profondeur,
    )
    return total


@shared_task
def cycle_ingestion():
    """Orchestre un cycle complet de collecte puis declenche le Matching."""
    logger.info("=== Debut du cycle d'ingestion ===")
    collecter_nvd_cve()
    enrichir_kev()
    collecter_cert_fr_avis()
    collecter_cert_fr_alertes()
    collecter_referentiels_normatifs()
    collecter_debian_security()
    collecter_ubuntu_usn()
    collecter_github_advisories()
    collecter_catalogue_actifs()
    calculer_matching()
    logger.info("=== Fin du cycle d'ingestion ===")
