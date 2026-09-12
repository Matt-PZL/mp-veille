"""
Taches Celery de collecte (boucle ~12h, cf. brief section 2).

Chaque source alimente `normaliser_et_ecrire_bdp`, qui est le seul point
d'ecriture dans la BDP (jamais d'ecrasement : versionning parent/enfant).
Le declenchement du Matching se fait juste apres, dans `cycle_ingestion`.

Stubs pour l'instant — les connecteurs reels (NVD, CERT-FR, ISO/CNIL/ANSSI/
DORA) restent a implementer.
"""

from celery import shared_task

from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching


def normaliser_et_ecrire_bdp(item: dict) -> Renseignement:
    """Cree ou met a jour (par nouvelle version) un Renseignement a partir
    d'un item normalise {type, titre, description, source, reference_externe,
    criticite, taxonomie_*, decouvert_le, id_source_stable}.
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


@shared_task
def collecter_nvd_cve():
    """Stub : collecte NVD/CVE. A implementer."""
    return 0


@shared_task
def collecter_cert_fr():
    """Stub : collecte bulletins CERT-FR/ANSSI. A implementer."""
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
