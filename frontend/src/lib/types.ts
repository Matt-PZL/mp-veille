// Formes renvoyees par l'API Django (cf. apps/api/schemas.py).
// A regenerer depuis /api/openapi.json si les schemas evoluent.

export type Criticite = "critique" | "elevee" | "moyenne" | "faible" | "";
export type Statut = "a_traiter" | "en_cours" | "clos" | "non_applicable";

export type Renseignement = {
  id: string;
  type: "technique" | "normatif";
  type_label: string;
  titre: string;
  description: string;
  source: string;
  url_source: string;
  reference: string;
  criticite: Criticite;
  criticite_label: string;
  nature: string;
  nature_label: string;
  cvss_score: number | null;
  cvss_vector: string;
  taxonomie_editeur: string;
  taxonomie_produit: string;
  taxonomie_version: string;
  taxonomie_referentiel: string;
  decouvert_le: string;
  consulte: boolean;
};

/** Pourquoi ce renseignement remonte au client (cf. apps/matching). */
export type MatchInfo = { palier: string; confiance: number; pourcent: number };

export type Actif = {
  id: number;
  type: "technique" | "normatif";
  categorie: string;
  editeur: string;
  produit: string;
  version: string;
  referentiel: string;
  libelle: string;
  nb_traitements: number;
  couvert: boolean;
};

export type ActifDuFeed = {
  id: number;
  type: "technique" | "normatif";
  libelle: string;
  version: string;
  nb: number;
  nb_critiques: number;
};

export type TraitementBref = {
  id: number;
  statut: Statut;
  statut_label: string;
  echeance: string | null;
  en_retard: boolean;
  maj_le: string;
};

export type TraitementDetail = TraitementBref & {
  id_renseignement: string;
  actif: Actif | null;
  justificatif: string;
  plan_action: string;
  passage_cab: boolean | null;
  preuve_fichier_url: string | null;
  historique: { evenement: string; horodatage: string }[];
};

export type FeedItem = {
  renseignement: Renseignement;
  traitement: TraitementBref | null;
  match: MatchInfo | null;
};

/** Stats du perimetre choisi (tout le client, ou l'actif filtre), calculees
 * AVANT tout filtre d'affichage — ne bougent jamais quand on change criticite/statut. */
export type RenseignementsStats = {
  nb_renseignements: number;
  nb_ouverts: number;
  par_etape: Record<string, number>;
  par_criticite_ouverts: Record<string, number>;
  nb_non_consultes: number;
};

export type RenseignementsListe = { items: FeedItem[]; stats: RenseignementsStats };

export type RenseignementDetail = {
  renseignement: Renseignement;
  traitement: TraitementDetail | null;
  match: MatchInfo | null;
  cvss_axes: { code: string; label: string; valeur: string }[];
};

export type TraitementItem = {
  traitement: TraitementDetail;
  renseignement: Renseignement | null;
};

export type Dashboard = {
  nb_renseignements: number;
  nb_ouverts: number;
  nb_actifs: number;
  nb_actifs_technique: number;
  nb_actifs_clean: number;
  nb_actifs_avec_non_traites: number;
  nb_referentiels: number;
  derniere_collecte: string | null;
  par_criticite: Record<string, number>;
  par_criticite_ouverts: Record<string, number>;
  par_etape: Record<string, number>;
  nb_non_consultes: number;
  nb_en_retard: number;
  taux_cloture: number | null;
  delai_moyen_jours: number | null;
  prioritaires: Renseignement[];
  derniers: Renseignement[];
  echeances: { id_renseignement: string; actif: string; titre: string; echeance: string | null }[];
  sante: { niveau: "ok" | "warn"; titre: string; detail: string }[];
  activite: { label: string; n: number }[];
  activite_max: number;
  onboarding: { cle: string; fait: boolean }[];
  onboarding_termine: boolean;
};

export type Utilisateur = { username: string; email: string };
export type Preferences = { seuil_criticite: string; frequence: string };
export type StatsActifs = { total: number; technique: number; normatif: number; non_couverts: number };
export type CompteursTraitement = Record<string, number>;
export type ProduitCatalogue = { categorie: string; editeur: string; produit: string; versions: string[] };
export type HistoriqueActif = {
  id: number;
  actif_repr: string;
  evenement: string;
  evenement_label: string;
  detail: string;
  horodatage: string;
};
