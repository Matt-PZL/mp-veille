"""
Moteur de Matching.

Regles (brief section 2) :
- Lecture seule sur BDP + BDC. N'ecrit JAMAIS nulle part.
- Ne lit que des champs non sensibles (taxonomie, statut) : aucun champ
  chiffre de la BDC n'est touche ici (voir apps/bdc/fields.EncryptedTextField).
- Declenche (a) apres chaque cycle d'ingestion, (b) juste apres une
  modification du profil client. JAMAIS a l'ouverture du panel.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.bdc.models import ActifClient
from apps.bdp.models import Renseignement


@dataclass(frozen=True)
class ResultatMatching:
    actif: ActifClient
    renseignement: Renseignement


def calculer_matching(actifs=None) -> list[ResultatMatching]:
    """Calcule les renseignements pertinents pour un ensemble d'actifs clients.

    V1 : correspondance exacte editeur+produit (technique) ou referentiel
    (normatif). A affiner (plages de version, alias de nommage...) une fois
    la taxonomie stabilisee.
    """
    actifs = actifs if actifs is not None else ActifClient.objects.all()
    resultats: list[ResultatMatching] = []

    for actif in actifs:
        qs = Renseignement.objects.filter(type=actif.type)
        if actif.type == "technique":
            if not (actif.editeur and actif.produit):
                continue
            qs = qs.filter(taxonomie_editeur=actif.editeur, taxonomie_produit=actif.produit)
        else:
            if not actif.referentiel:
                continue
            qs = qs.filter(taxonomie_referentiel=actif.referentiel)

        resultats.extend(ResultatMatching(actif=actif, renseignement=r) for r in qs)

    return resultats
