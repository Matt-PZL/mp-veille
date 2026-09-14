"""
Conversion modeles Django -> formes exposees par l'API.

Centralise ici plutot que dans chaque routeur : c'est le seul endroit qui
decide ce qui sort vers le front, donc le seul a auditer pour verifier
qu'aucun champ sensible ne fuit dans une liste.
"""

from __future__ import annotations

from apps.bdc.models import ActifClient, Traitement
from apps.bdp.models import Renseignement


def actif_out(actif: ActifClient, *, couvert: bool = True, nb_traitements: int | None = None) -> dict:
    return {
        "id": actif.pk,
        "type": actif.type,
        "categorie": actif.categorie,
        "editeur": actif.editeur,
        "produit": actif.produit,
        "version": actif.version,
        "referentiel": actif.referentiel,
        "libelle": str(actif),
        "nb_traitements": actif.traitements.count() if nb_traitements is None else nb_traitements,
        "couvert": couvert,
    }


def renseignement_out(r: Renseignement, *, consulte: bool = False) -> dict:
    return {
        "id": r.id_renseignement_bdp,
        "type": r.type,
        "type_label": r.get_type_display() or "",
        "titre": r.titre,
        "description": r.description,
        "source": r.source,
        "url_source": r.url_source,
        # `reference_courte` retire le suffixe technique `::produit` que
        # l'ingestion CERT-FR ajoute pour l'unicite — il ne doit jamais
        # atteindre l'interface.
        "reference": r.reference_courte,
        "criticite": r.criticite,
        "criticite_label": r.get_criticite_display() or "",
        "nature": r.nature,
        "nature_label": r.get_nature_display() or "",
        "cvss_score": r.cvss_score,
        "cvss_vector": r.cvss_vector,
        "taxonomie_editeur": r.taxonomie_editeur,
        "taxonomie_produit": r.taxonomie_produit,
        "taxonomie_version": r.taxonomie_version,
        "taxonomie_referentiel": r.taxonomie_referentiel,
        "decouvert_le": r.decouvert_le,
        "consulte": consulte,
        "auteur": r.auteur,
        "niveau_confiance": r.niveau_confiance,
        "niveau_confiance_label": r.get_niveau_confiance_display() or "",
        "tags": r.tags,
        "secteur_concerne": r.secteur_concerne,
        "tlp": r.tlp,
        "cve_associees": r.cve_associees,
        "ioc_associees": r.ioc_associees,
    }


def traitement_bref(t: Traitement) -> dict:
    """Forme de liste : volontairement sans justificatif ni plan d'action,
    qui sont chiffres au repos et n'ont pas a transiter en masse."""
    return {
        "id": t.pk,
        "statut": t.statut,
        "statut_label": t.get_statut_display(),
        "echeance": t.echeance,
        "en_retard": t.en_retard,
        "maj_le": t.maj_le,
    }


def traitement_detail(t: Traitement, *, couverts: set[int] | None = None) -> dict:
    donnees = traitement_bref(t)
    donnees.update(
        {
            "id_renseignement": t.id_renseignement_bdp,
            "actif": actif_out(t.actif, couvert=(couverts is None or t.actif.pk in couverts))
            if t.actif
            else None,
            "justificatif": t.justificatif or "",
            "plan_action": t.plan_action or "",
            "passage_cab": t.passage_cab,
            "preuve_fichier_url": t.preuve_fichier.url if t.preuve_fichier else None,
            "historique": [
                {"evenement": h.evenement, "horodatage": h.horodatage}
                for h in t.historique.all()
            ],
        }
    )
    return donnees


def match_info(entree: dict | None) -> dict | None:
    """`entree` vient de la table {uuid: {confiance, palier, pourcent}}
    construite a partir des resultats du Matching."""
    if not entree:
        return None
    return {
        "palier": entree["palier"],
        "confiance": entree["confiance"],
        "pourcent": entree["pourcent"],
    }


def paliers_par_renseignement(resultats) -> dict:
    """Meilleur palier de correspondance par renseignement.

    Un meme renseignement peut matcher plusieurs actifs du client : on ne
    garde que la correspondance la plus sure pour l'affichage.
    """
    table: dict = {}
    for r in resultats:
        cle = r.renseignement.id_renseignement_bdp
        precedent = table.get(cle)
        if precedent is None or r.confiance > precedent["confiance"]:
            table[cle] = {
                "confiance": r.confiance,
                "palier": r.palier,
                "pourcent": int(round(r.confiance * 100)),
            }
    return table


def cvss_axes(r: Renseignement) -> list[dict]:
    details = r.cvss_details()
    if not details:
        return []
    return [{"code": d["code"], "label": d["champ"], "valeur": d["valeur"]} for d in details]
