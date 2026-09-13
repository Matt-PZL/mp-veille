"""
Taches Celery de collecte (boucle ~12h, cf. brief section 2).

Chaque source alimente `normaliser_et_ecrire_bdp`, qui est le seul point
d'ecriture dans la BDP (jamais d'ecrasement : versionning parent/enfant).
Le declenchement du Matching se fait juste apres, dans `cycle_ingestion`.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from celery import shared_task
from django.utils import timezone

from apps.bdc.models import ActifClient
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_SEVERITE_NVD = {"CRITICAL": "critique", "HIGH": "elevee", "MEDIUM": "moyenne", "LOW": "faible"}

CERT_FR_INDEX = "https://www.cert.ssi.gouv.fr/avis/json/"
CERT_FR_DETAIL = "https://www.cert.ssi.gouv.fr/avis/{ref}/json/"
CERT_FR_PAGE = "https://www.cert.ssi.gouv.fr/avis/{ref}/"
CERT_FR_LOOKBACK_JOURS = 30

CNIL_RSS = "https://www.cnil.fr/fr/rss.xml"

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

    for i, actif in enumerate(actifs):
        if i:
            time.sleep(6)

        params = urllib.parse.urlencode({"keywordSearch": actif.produit, "resultsPerPage": 5})
        req = urllib.request.Request(
            f"{NVD_API}?{params}",
            headers={"User-Agent": "veille-saas/0.1 (POC interne, contact: matt)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError):
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


@shared_task
def collecter_cert_fr(lookback_jours: int = CERT_FR_LOOKBACK_JOURS):
    """Collecte reelle des avis de securite CERT-FR (ANSSI) via l'export
    JSON officiel (`/avis/json/` puis `/avis/<ref>/json/`).

    Un avis peut couvrir plusieurs produits/editeurs (`affected_systems`) :
    on cree un Renseignement par couple editeur+produit distinct pour que
    le Matching (exact editeur+produit) puisse s'appliquer, exactement comme
    pour un CVE NVD.

    Fenetre glissante de `lookback_jours` (30 par defaut) sur la date de
    derniere revision, pour eviter de reparcourir en detail les ~17 000 avis
    de l'historique CERT-FR a chaque cycle ; un avis deja connu et non
    revise depuis n'est pas retelecharge."""
    try:
        index = _get_json(CERT_FR_INDEX)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return 0

    seuil = timezone.now() - timedelta(days=lookback_jours)
    total = 0

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
            detail = _get_json(CERT_FR_DETAIL.format(ref=ref))
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue

        criticite = _certfr_criticite(detail.get("risks", []))
        url_avis = CERT_FR_PAGE.format(ref=ref)
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
            # Avis sans produit structure (rare) : conserve quand meme,
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

    return total


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

    Limite connue : il n'existe pas, a ce jour, de flux public structure
    equivalent pour NIS2 / ISO 27001 / DORA (ISO est payant ; NIS2/DORA sont
    du texte legal EUR-Lex sans flux exploitable simplement) — a specifier
    au cas par cas si un client declare l'un de ces referentiels."""
    try:
        req = urllib.request.Request(CNIL_RSS, headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read()
    except (urllib.error.URLError, TimeoutError):
        return 0

    try:
        items = _parser_rss(payload)
    except ET.ParseError:
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

    return total


@shared_task
def cycle_ingestion():
    """Orchestre un cycle complet de collecte puis declenche le Matching."""
    collecter_nvd_cve()
    collecter_cert_fr()
    collecter_referentiels_normatifs()
    calculer_matching()
