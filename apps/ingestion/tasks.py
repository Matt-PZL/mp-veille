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
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from apps.bdc.models import ActifClient
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_SEVERITE_NVD = {"CRITICAL": "critique", "HIGH": "elevee", "MEDIUM": "moyenne", "LOW": "faible"}


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
        reference_externe=item.get("reference_externe", ""),
        criticite=item.get("criticite", ""),
        taxonomie_categorie=item.get("taxonomie_categorie", ""),
        taxonomie_editeur=item.get("taxonomie_editeur", ""),
        taxonomie_produit=item.get("taxonomie_produit", ""),
        taxonomie_version=item.get("taxonomie_version", ""),
        taxonomie_referentiel=item.get("taxonomie_referentiel", ""),
        decouvert_le=item["decouvert_le"],
    )


def _contenu_modifie(existant: Renseignement, item: dict) -> bool:
    return existant.description != item["description"] or existant.criticite != item.get(
        "criticite", ""
    )


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

            normaliser_et_ecrire_bdp({
                "type": "technique",
                "titre": f"{cve_id} — {actif.produit}",
                "description": _nvd_description(cve)[:2000] or "(pas de description disponible)",
                "source": "NVD",
                "reference_externe": cve_id,
                "criticite": _nvd_severite(cve),
                "taxonomie_editeur": actif.editeur,
                "taxonomie_produit": actif.produit,
                "taxonomie_version": actif.version,
                "decouvert_le": publie,
            })
            total += 1

    return total


@shared_task
def collecter_cert_fr():
    """Stub : collecte bulletins CERT-FR/ANSSI. A implementer (flux RSS/JSON
    du CERT-FR n'a pas de schema stable public simple — a specifier)."""
    return 0


@shared_task
def collecter_referentiels_normatifs():
    """Stub : collecte ISO/CNIL/ANSSI/DORA. A implementer."""
    return 0


@shared_task
def cycle_ingestion():
    """Orchestre un cycle complet de collecte puis declenche le Matching."""
    collecter_nvd_cve()
    collecter_cert_fr()
    collecter_referentiels_normatifs()
    calculer_matching()
