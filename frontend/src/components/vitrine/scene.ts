import type { CleLogo } from "./logos";

/**
 * Donnees de la scene du hero.
 *
 * Regle absolue de ce fichier : rien n'y est invente. Chaque correspondance
 * affichee renvoie a un renseignement reellement publie, avec sa reference et
 * son score d'origine (colonne `source`). Un RSSI qui verifie une seule ligne
 * doit la retrouver telle quelle chez l'emetteur.
 *
 * Le vocabulaire suit le modele reel (apps/bdp/models.py) :
 *   - `nature`    reprend NATURE_CHOICES
 *   - `criticite` reprend CRITICITE_CHOICES
 * La palette du hero n'est donc pas un neon decoratif : c'est l'echelle de
 * criticite du produit, poussee en luminance pour tenir le bloom.
 */

/** Natures du modele, plus `fuite` — cf. note en bas de fichier. */
export type NatureScene = "vulnerabilite" | "correctif" | "reglementaire" | "information" | "fuite";

/** Criticites du modele, plus `normatif` pour les echeances de conformite. */
export type CriticiteScene = "critique" | "elevee" | "moyenne" | "faible" | "normatif";

export type EtatCible =
  /** Aucun renseignement ne remonte sur cet actif. */
  | { code: "ras" }
  /** Le moteur de matching travaille : pas encore de correspondance etablie. */
  | { code: "analyse" }
  /** Une correspondance actif <-> renseignement, telle que la produit le matching. */
  | {
      code: "correspondance";
      nature: NatureScene;
      criticite: CriticiteScene;
      /** Ligne principale de la fiche : la reference du renseignement. */
      libelle: string;
      /** Ligne secondaire : score, exploitabilite, correctif. */
      detail: string;
      /** Emetteur du renseignement, affiche tel quel. */
      source: string;
    };

export type CibleScene = {
  id: string;
  /** Nom de l'actif tel qu'il apparait dans le parc. */
  libelle: string;
  /** Version declaree — c'est elle qui rend la correspondance verifiable. */
  version: string;
  type: "technique" | "normatif";
  /** `null` pour les referentiels, affiches en pastille texte. */
  logo: CleLogo | null;
  /**
   * Code court affiche dans le cadre quand il n'y a pas de logo.
   *
   * Un referentiel n'a pas de marque a montrer : le cadre porte son code, et
   * l'etiquette sa designation complete — meme partage que logo / nom pour un
   * actif technique, pas une repetition.
   */
  sigle?: string;
  /** Position normalisee 0..1 dans la zone de scene (pas dans le hero). */
  x: number;
  y: number;
  /**
   * Presence et position en disposition compacte (sous 1100px).
   *
   * Dix cibles dans la largeur d'un telephone se recouvrent : la scene
   * compacte n'en garde que cinq, choisies pour couvrir tous les etats de
   * fiche (correspondance critique, analyse, RAS, fuite, echeance normative).
   * Une cible sans `compact` disparait de la scene ET du parcours.
   */
  compact?: { x: number; y: number };
  etat: EtatCible;
};

export const CIBLES: CibleScene[] = [
  {
    id: "ingress-nginx",
    libelle: "ingress-nginx",
    version: "1.11.4",
    type: "technique",
    logo: "kubernetes",
    x: 0.14,
    y: 0.14,
    compact: { x: 0.22, y: 0.12 },
    etat: {
      code: "correspondance",
      nature: "vulnerabilite",
      criticite: "critique",
      libelle: "CVE-2025-1974",
      detail: "CVSS 9.8 · exploit public · corrigé en 1.12.1",
      source: "NVD",
    },
  },
  {
    id: "nginx",
    libelle: "nginx",
    version: "1.20.0",
    type: "technique",
    logo: "nginx",
    x: 0.46,
    y: 0.05,
    etat: {
      code: "correspondance",
      nature: "vulnerabilite",
      criticite: "elevee",
      libelle: "CVE-2021-23017",
      detail: "CVSS 7.7 · résolveur DNS · corrigé en 1.20.1",
      source: "NVD",
    },
  },
  {
    id: "openssl",
    libelle: "OpenSSL",
    version: "3.0.6",
    type: "technique",
    logo: "openssl",
    x: 0.79,
    y: 0.19,
    etat: {
      code: "correspondance",
      nature: "correctif",
      criticite: "elevee",
      libelle: "CVE-2022-3602",
      detail: "CVSS 7.5 · correctif disponible en 3.0.7",
      source: "NVD",
    },
  },
  {
    id: "postgresql",
    libelle: "PostgreSQL",
    version: "16.2",
    type: "technique",
    logo: "postgresql",
    x: 0.28,
    y: 0.44,
    compact: { x: 0.78, y: 0.3 },
    etat: { code: "analyse" },
  },
  {
    id: "ubuntu",
    libelle: "Ubuntu",
    version: "22.04 LTS",
    type: "technique",
    logo: "ubuntu",
    x: 0.6,
    y: 0.38,
    etat: {
      code: "correspondance",
      nature: "information",
      criticite: "moyenne",
      libelle: "CERTFR-2026-AVI-0926",
      detail: "Vulnérabilités du noyau Linux · avis éditeur",
      source: "CERT-FR",
    },
  },
  {
    id: "redis",
    libelle: "Redis",
    version: "7.2.4",
    type: "technique",
    logo: "redis",
    x: 0.9,
    y: 0.52,
    compact: { x: 0.3, y: 0.52 },
    etat: { code: "ras" },
  },
  {
    id: "nodejs",
    libelle: "Node.js",
    version: "20.11 LTS",
    type: "technique",
    logo: "nodejs",
    x: 0.1,
    y: 0.72,
    etat: { code: "ras" },
  },
  {
    id: "gitlab",
    libelle: "GitLab",
    version: "16.9",
    type: "technique",
    logo: "gitlab",
    x: 0.42,
    y: 0.68,
    compact: { x: 0.75, y: 0.7 },
    etat: {
      code: "correspondance",
      nature: "fuite",
      criticite: "elevee",
      libelle: "FUITE DE DONNÉES",
      detail: "Identifiants de votre périmètre exposés",
      source: "Veille fuites",
    },
  },
  {
    id: "iso-27001",
    libelle: "ISO/IEC 27001",
    version: ":2022",
    type: "normatif",
    logo: null,
    sigle: "27001",
    x: 0.66,
    y: 0.82,
    compact: { x: 0.25, y: 0.88 },
    etat: {
      code: "correspondance",
      nature: "reglementaire",
      criticite: "normatif",
      libelle: "ÉCHÉANCE J-90",
      detail: "Audit de surveillance · 3 mesures ouvertes",
      source: "Plan de conformité",
    },
  },
  {
    id: "nis2",
    libelle: "Directive NIS2",
    version: "UE 2022/2555",
    type: "normatif",
    logo: null,
    sigle: "NIS2",
    x: 0.88,
    y: 0.9,
    etat: {
      code: "correspondance",
      nature: "reglementaire",
      criticite: "normatif",
      libelle: "ÉCHÉANCE J-42",
      detail: "Revue du périmètre · 2 mesures ouvertes",
      source: "Plan de conformité",
    },
  },
];

/**
 * Ordre de parcours du reticule.
 *
 * Volontairement different de l'ordre du tableau : le trajet doit balayer la
 * scene au lieu de descendre en colonne, et la correspondance critique passe
 * en premier pour que l'ouverture de la boucle porte le propos.
 */
export const ORDRE_VISITE = [
  "ingress-nginx",
  "openssl",
  "redis",
  "nis2",
  "gitlab",
  "nodejs",
  "postgresql",
  "nginx",
  "ubuntu",
  "iso-27001",
] as const;

/** Cible verrouillee au premier rendu — identique serveur et client. */
export const CIBLE_INITIALE = "ingress-nginx";

/**
 * NOTE PRODUIT — `nature: "fuite"`
 *
 * Les quatre natures du modele sont vulnerabilite / correctif / reglementaire
 * / information. La fuite de donnees n'y figure pas encore : la fiche GitLab
 * anticipe une fonction prevue, elle ne decrit pas l'existant. A retirer ou a
 * brancher sur le modele reel avant la mise en ligne publique si la fonction
 * n'est pas livree d'ici la.
 */

/**
 * Criticite effective d'une cible, y compris hors correspondance.
 *
 * Un actif sans renseignement est au plus bas de l'echelle, un actif en cours
 * d'analyse au milieu : la couleur reste donc toujours celle de l'echelle du
 * produit, jamais un code decoratif ajoute pour la scene.
 */
export function criticiteDe(etat: EtatCible): CriticiteScene {
  if (etat.code === "ras") return "faible";
  if (etat.code === "analyse") return "moyenne";
  return etat.criticite;
}
