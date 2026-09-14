"""
Moteur de Matching.

Regles (brief section 2) :
- Lecture seule sur BDP + BDC. N'ecrit JAMAIS nulle part.
- Ne lit que des champs non sensibles (taxonomie, statut) : aucun champ
  chiffre de la BDC n'est touche ici (voir apps/bdc/fields.EncryptedTextField).
- Declenche (a) apres chaque cycle d'ingestion, (b) juste apres une
  modification du profil client.

V2 : correspondance tolerante. La V1 comparait `taxonomie_editeur` et
`taxonomie_produit` a l'identique, ce qui ne matchait en pratique que les
renseignements dont NOUS avions ecrit la taxonomie (collecter_nvd_cve recopie
le nom de l'actif du client) — les ~100 avis CERT-FR d'un cycle, qui suivent
la nomenclature de l'ANSSI, ne tombaient jamais pile dessus.

On compare desormais des formes canoniques (sans accents, sans ponctuation,
suffixes corporatifs retires, alias connus appliques — cf. `normalisation`),
par paliers de confiance decroissante. Chaque resultat porte sa confiance et
le palier qui l'a produit, pour que l'interface puisse un jour distinguer
« c'est exactement ton produit » de « ca parle probablement de ton produit ».
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.db.models import Q

from collections import Counter

from apps.bdc.models import ActifClient, Traitement
from apps.bdp.models import Renseignement

from .normalisation import (
    canoniser_editeur,
    canoniser_produit,
    canoniser_referentiel,
    jaccard,
    tokens,
    tokens_distinctifs,
)

# Paliers, de la correspondance la plus sure a la plus permissive.
CONFIANCE_EXACTE = 1.0       # editeur ET produit canoniques identiques
CONFIANCE_PRODUIT = 0.9      # produit identique, editeur absent d'un cote
CONFIANCE_INCLUSION = 0.75   # un nom contient l'autre (« Cisco Firepower Threat Defense »)
CONFIANCE_RECOUVREMENT = 0.6 # forte intersection des mots
CONFIANCE_TITRE = 0.55       # produit retrouve dans le titre de l'avis

# En dessous, on considere que ce n'est pas le produit du client.
SEUIL_MINIMAL = 0.55

# Recouvrement minimal de mots pour retenir le palier CONFIANCE_RECOUVREMENT.
_JACCARD_MINIMAL = 0.6

# Un mot d'au moins cette longueur est juge assez distinctif pour autoriser
# une correspondance par le titre. « ad » ou « os » ne le sont pas.
_LONGUEUR_TOKEN_DISTINCTIF = 4


@dataclass(frozen=True)
class ResultatMatching:
    actif: ActifClient
    renseignement: Renseignement
    confiance: float = CONFIANCE_EXACTE
    palier: str = "exact"


def _q_candidats_technique(actif: ActifClient) -> Q | None:
    """Pre-filtre SQL grossier pour un actif technique.

    Le score fin se calcule en Python (la canonisation n'existe pas en SQL),
    mais on evite de charger toute la BDP : seuls les renseignements dont le
    produit, l'editeur ou le titre contient un mot distinctif de l'actif sont
    remontes. `icontains` est insensible a la casse cote PostgreSQL.
    """
    mots = [t for t in tokens_distinctifs(actif.produit) if len(t) >= 3]
    if not mots:
        return None
    clauses = []
    for mot in mots:
        clauses.append(Q(taxonomie_produit__icontains=mot))
        clauses.append(Q(titre__icontains=mot))
    editeur = canoniser_editeur(actif.editeur)
    if editeur:
        for mot in editeur.split():
            if len(mot) >= 3:
                clauses.append(Q(taxonomie_editeur__icontains=mot))
    return reduce(or_, clauses)


def _editeurs_compatibles(editeur_actif: str, editeur_rens: str) -> bool:
    """Deux editeurs canoniques se contredisent-ils ?

    Un editeur absent d'un cote ne contredit rien (le CERT-FR ne renseigne pas
    toujours l'editeur) — on ne bloque que sur un desaccord explicite.
    """
    if not editeur_actif or not editeur_rens:
        return True
    if editeur_actif == editeur_rens:
        return True
    # « palo alto » vs « palo alto networks » : l'un prefixe l'autre.
    return editeur_actif.startswith(editeur_rens) or editeur_rens.startswith(editeur_actif)


def _score_technique(actif: ActifClient, rens: Renseignement) -> tuple[float, str] | None:
    """Confiance et palier d'un couple actif technique / renseignement."""
    produit_actif = canoniser_produit(actif.produit)
    if not produit_actif:
        return None

    editeur_actif = canoniser_editeur(actif.editeur)
    editeur_rens = canoniser_editeur(rens.taxonomie_editeur)
    if not _editeurs_compatibles(editeur_actif, editeur_rens):
        return None

    produit_rens = canoniser_produit(rens.taxonomie_produit)

    if produit_rens:
        if produit_actif == produit_rens:
            # Les deux editeurs presents et concordants : correspondance sure.
            if editeur_actif and editeur_rens:
                return CONFIANCE_EXACTE, "exact"
            return CONFIANCE_PRODUIT, "produit"

        mots_actif = tokens(produit_actif)
        mots_rens = tokens(produit_rens)
        # « Firepower Threat Defense » vs « Cisco Firepower Threat Defense »
        if mots_actif <= mots_rens or mots_rens <= mots_actif:
            return CONFIANCE_INCLUSION, "inclusion"
        if jaccard(mots_actif, mots_rens) >= _JACCARD_MINIMAL:
            return CONFIANCE_RECOUVREMENT, "recouvrement"
        return None

    # Le renseignement ne nomme pas de produit (CERT-FR met « N/A ») : on
    # cherche le produit du client dans le titre de l'avis, a condition qu'il
    # soit assez distinctif pour ne pas ramener n'importe quoi.
    distinctifs = tokens_distinctifs(actif.produit)
    if not distinctifs or not any(len(t) >= _LONGUEUR_TOKEN_DISTINCTIF for t in distinctifs):
        return None
    if distinctifs <= tokens(rens.titre):
        return CONFIANCE_TITRE, "titre"
    return None


def _score_normatif(actif: ActifClient, rens: Renseignement) -> tuple[float, str] | None:
    """Confiance et palier d'un couple actif normatif / renseignement."""
    ref_actif = canoniser_referentiel(actif.referentiel)
    if not ref_actif:
        return None
    ref_rens = canoniser_referentiel(rens.taxonomie_referentiel)

    if ref_rens:
        if ref_actif == ref_rens:
            return CONFIANCE_EXACTE, "exact"
        mots_actif, mots_rens = tokens(ref_actif), tokens(ref_rens)
        if mots_actif <= mots_rens or mots_rens <= mots_actif:
            return CONFIANCE_INCLUSION, "inclusion"
        return None

    if tokens(ref_actif) <= tokens(rens.titre):
        return CONFIANCE_TITRE, "titre"
    return None


def calculer_matching(actifs=None, seuil: float = SEUIL_MINIMAL) -> list[ResultatMatching]:
    """Renseignements pertinents pour un ensemble d'actifs clients.

    Retourne au plus un resultat par couple (actif, renseignement) : si
    plusieurs paliers s'appliquent, seul le plus confiant est conserve. Les
    resultats sont tries par confiance decroissante puis par date de
    decouverte, pour que l'appelant puisse tronquer sans perdre le meilleur.
    """
    actifs = actifs if actifs is not None else ActifClient.objects.all()
    resultats: list[ResultatMatching] = []

    for actif in actifs:
        if actif.type == "technique":
            filtre = _q_candidats_technique(actif)
            if filtre is None:
                continue
            candidats = Renseignement.objects.filter(Q(type="technique") & filtre)
            scorer = _score_technique
        else:
            ref = canoniser_referentiel(actif.referentiel)
            if not ref:
                continue
            mots = [m for m in ref.split() if len(m) >= 2]
            filtre = reduce(
                or_,
                [Q(taxonomie_referentiel__icontains=m) | Q(titre__icontains=m) for m in mots],
            )
            candidats = Renseignement.objects.filter(Q(type="normatif") & filtre)
            scorer = _score_normatif

        for rens in candidats:
            score = scorer(actif, rens)
            if score is None or score[0] < seuil:
                continue
            confiance, palier = score
            resultats.append(
                ResultatMatching(
                    actif=actif, renseignement=rens, confiance=confiance, palier=palier
                )
            )

    resultats.sort(key=lambda r: (-r.confiance, -r.renseignement.decouvert_le.timestamp()))
    return resultats


# --------------------------------------------------------------------------
# Statistiques de perimetre — point d'entree unique.
#
# Avant ceci, dashboard.py / renseignements.py / traitement.py recalculaient
# chacun leurs propres agregats, sur des populations differentes (certains
# scopes sur le Matching, d'autres sur Traitement.objects.all() brut) : les
# compteurs affiches divergaient selon la page. Toute agregation « combien de
# renseignements / actifs / de quel statut » doit desormais passer par
# calculer_perimetre_stats(), jamais etre recalculee localement dans un routeur.


@dataclass(frozen=True)
class PerimetreStats:
    nb_renseignements: int
    nb_ouverts: int
    par_etape: dict[str, int]
    par_criticite: dict[str, int]
    par_criticite_ouverts: dict[str, int]
    nb_actifs: int
    nb_actifs_clean: int
    nb_actifs_avec_non_traites: int


def actifs_avec_renseignements_ouverts() -> set[int]:
    """PKs des ActifClient couverts par au moins un renseignement pertinent
    dont le traitement est encore ouvert (a_traiter/en_cours)."""
    resultats = calculer_matching()
    traitements = {t.id_renseignement_bdp: t for t in Traitement.objects.all()}
    return {
        r.actif.pk
        for r in resultats
        if getattr(traitements.get(r.renseignement.id_renseignement_bdp), "statut", "a_traiter")
        in _OUVERTS
    }


_OUVERTS = ("a_traiter", "en_cours")


def calculer_perimetre_stats(actif_id: int | None = None) -> PerimetreStats:
    """Chiffres agreges sur le perimetre du client (calculer_matching(),
    dedupliques), ou sur un seul actif si `actif_id` est fourni.

    Filtrer par criticite/statut cote appelant ne doit JAMAIS repasser par
    cette fonction avec un scope different : les stats retournees decrivent
    toujours le perimetre choisi (tout le client, ou un seul actif) dans son
    ensemble, independamment de tout filtre d'affichage applique ensuite a la
    liste — c'est ce qui garantit qu'elles ne bougent pas quand on filtre.
    """
    resultats_total = calculer_matching()
    resultats = (
        resultats_total
        if actif_id is None
        else [r for r in resultats_total if r.actif.pk == actif_id]
    )

    pertinents = list(
        {r.renseignement.id_renseignement_bdp: r.renseignement for r in resultats}.values()
    )
    traitements = {t.id_renseignement_bdp: t for t in Traitement.objects.all()}

    def statut_de(r):
        return getattr(traitements.get(r.id_renseignement_bdp), "statut", "a_traiter")

    par_etape = Counter(statut_de(r) for r in pertinents)
    ouverts = [r for r in pertinents if statut_de(r) in _OUVERTS]
    par_criticite = Counter(r.criticite or "moyenne" for r in pertinents)
    par_criticite_ouverts = Counter(r.criticite or "moyenne" for r in ouverts)

    nb_actifs = ActifClient.objects.count()
    nb_actifs_clean = nb_actifs_avec_non_traites = 0
    if actif_id is None:
        actifs_ouverts = actifs_avec_renseignements_ouverts()
        nb_actifs_avec_non_traites = len(actifs_ouverts)
        nb_actifs_clean = nb_actifs - nb_actifs_avec_non_traites

    return PerimetreStats(
        nb_renseignements=len(pertinents),
        nb_ouverts=len(ouverts),
        par_etape=dict(par_etape),
        par_criticite=dict(par_criticite),
        par_criticite_ouverts=dict(par_criticite_ouverts),
        nb_actifs=nb_actifs,
        nb_actifs_clean=nb_actifs_clean,
        nb_actifs_avec_non_traites=nb_actifs_avec_non_traites,
    )
