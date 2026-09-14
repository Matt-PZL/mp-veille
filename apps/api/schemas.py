"""
Schemas de l'API.

Ce sont eux qui produisent l'OpenAPI dont le front derive ses types
TypeScript : toute forme de donnee exposee au front passe par ici, jamais
un dict construit a la main dans une vue.

Regle d'architecture conservee : les champs chiffres de la BDC (justificatif,
plan d'action) ne sont serialises que dans le detail d'un traitement, pour
l'utilisateur authentifie qui en est proprietaire — jamais dans les listes.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from ninja import Schema


# --------------------------------------------------------------------------
# Renseignements (BDP)
# --------------------------------------------------------------------------
class CvssAxe(Schema):
    label: str
    valeur: str
    code: str


class RenseignementOut(Schema):
    id: UUID
    type: str
    type_label: str
    titre: str
    description: str
    source: str
    url_source: str
    reference: str
    criticite: str
    criticite_label: str
    nature: str
    nature_label: str
    cvss_score: float | None
    cvss_vector: str
    taxonomie_editeur: str
    taxonomie_produit: str
    taxonomie_version: str
    taxonomie_referentiel: str
    decouvert_le: datetime
    consulte: bool
    auteur: str
    niveau_confiance: str
    niveau_confiance_label: str
    tags: list[str]
    secteur_concerne: str
    tlp: str
    cve_associees: list[str]
    ioc_associees: list[str]


class MatchInfo(Schema):
    """Pourquoi ce renseignement remonte au client — cf. apps.matching."""

    palier: str
    confiance: float
    pourcent: int


class RenseignementListItem(Schema):
    renseignement: RenseignementOut
    traitement: "TraitementBref | None"
    match: MatchInfo | None


class RenseignementsStats(Schema):
    """Stats du perimetre choisi (tout le client, ou un seul actif) —
    calculees AVANT tout filtre d'affichage (criticite, statut...), donc
    stables quel que soit le filtre applique a `items` a cote."""

    nb_renseignements: int
    nb_ouverts: int
    par_etape: dict[str, int]
    par_criticite_ouverts: dict[str, int]
    nb_non_consultes: int


class RenseignementsListe(Schema):
    items: list[RenseignementListItem]
    stats: RenseignementsStats


class RenseignementDetail(Schema):
    renseignement: RenseignementOut
    traitement: "TraitementDetail | None"
    match: MatchInfo | None
    cvss_axes: list[CvssAxe]


# --------------------------------------------------------------------------
# Actifs (BDC)
# --------------------------------------------------------------------------
class ActifOut(Schema):
    id: int
    type: str
    categorie: str
    editeur: str
    produit: str
    version: str
    referentiel: str
    libelle: str
    nb_traitements: int
    couvert: bool


class ActifCreate(Schema):
    type: str
    categorie: str = ""
    editeur: str = ""
    produit: str = ""
    version: str = ""
    referentiel: str = ""


class ActifVersionUpdate(Schema):
    version: str


class HistoriqueActifOut(Schema):
    id: int
    actif_repr: str
    evenement: str
    evenement_label: str
    detail: str
    horodatage: datetime


# --------------------------------------------------------------------------
# Traitements (BDC)
# --------------------------------------------------------------------------
class TraitementBref(Schema):
    """Forme legere pour les listes : aucun champ chiffre."""

    id: int
    statut: str
    statut_label: str
    echeance: date | None
    en_retard: bool
    maj_le: datetime


class HistoriqueTraitementOut(Schema):
    evenement: str
    horodatage: datetime


class TraitementDetail(Schema):
    id: int
    id_renseignement: UUID
    statut: str
    statut_label: str
    echeance: date | None
    en_retard: bool
    maj_le: datetime
    actif: ActifOut | None
    # Champs chiffres au repos, dechiffres ici pour leur proprietaire.
    justificatif: str
    plan_action: str
    passage_cab: bool | None
    preuve_fichier_url: str | None
    historique: list[HistoriqueTraitementOut]


class TraitementListItem(Schema):
    traitement: TraitementDetail
    renseignement: RenseignementOut | None


class TraitementWrite(Schema):
    statut: str
    justificatif: str = ""
    plan_action: str = ""
    echeance: date | None = None
    passage_cab: bool | None = None


# --------------------------------------------------------------------------
# Tableau de bord
# --------------------------------------------------------------------------
class PointActivite(Schema):
    label: str
    n: int


class EtapeDashboard(Schema):
    """Jalon du parcours de mise en route."""

    cle: str
    fait: bool


class SanteItem(Schema):
    niveau: str  # "ok" | "warn"
    titre: str
    detail: str


class EcheanceOut(Schema):
    id_renseignement: UUID
    actif: str
    titre: str
    echeance: date | None


class DashboardOut(Schema):
    nb_renseignements: int
    nb_ouverts: int
    nb_actifs: int
    nb_actifs_technique: int
    nb_actifs_clean: int
    nb_actifs_avec_non_traites: int
    nb_referentiels: int
    derniere_collecte: datetime | None

    par_criticite: dict[str, int]
    par_criticite_ouverts: dict[str, int]
    par_etape: dict[str, int]
    nb_non_consultes: int
    nb_en_retard: int

    taux_cloture: int | None
    delai_moyen_jours: float | None

    prioritaires: list[RenseignementOut]
    derniers: list[RenseignementOut]
    echeances: list[EcheanceOut]
    sante: list[SanteItem]
    activite: list[PointActivite]
    activite_max: int

    onboarding: list[EtapeDashboard]
    onboarding_termine: bool


# --------------------------------------------------------------------------
# Compte et preferences
# --------------------------------------------------------------------------
class UtilisateurOut(Schema):
    username: str
    email: str


class PreferencesOut(Schema):
    seuil_criticite: str
    frequence: str
    afficher_compteurs_nav: bool


class PreferencesWrite(Schema):
    seuil_criticite: str
    frequence: str
    afficher_compteurs_nav: bool = True


class ConnexionIn(Schema):
    username: str
    password: str


class MessageOut(Schema):
    detail: str


# --------------------------------------------------------------------------
# Catalogue / taxonomie (aide a la saisie d'un actif)
# --------------------------------------------------------------------------
class ProduitCatalogue(Schema):
    categorie: str
    editeur: str
    produit: str
    versions: list[str]


RenseignementListItem.model_rebuild()
RenseignementDetail.model_rebuild()
