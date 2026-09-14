/**
 * Client de l'API Django.
 *
 * Auth par cookie de session : chaque requete part avec
 * `credentials: "include"`, et toute ecriture joint le jeton CSRF lu dans le
 * cookie `csrftoken`. Sans ce jeton, django-ninja repond 403 — c'est
 * volontaire, c'est ce qui empeche un site tiers de declencher une ecriture
 * au nom de l'utilisateur connecte.
 */

import type {
  Actif,
  ActifDuFeed,
  CompteursTraitement,
  Dashboard,
  FeedItem,
  HistoriqueActif,
  Preferences,
  ProduitCatalogue,
  Renseignement,
  RenseignementDetail,
  StatsActifs,
  TraitementDetail,
  TraitementItem,
  Utilisateur,
} from "./types";

// Meme origine que la page : le proxy defini dans next.config.ts relaie
// vers Django cote serveur. On ne cible plus jamais le backend directement
// depuis le navigateur (voir next.config.ts pour le pourquoi).
const BASE = "";

/** Erreur portant le detail renvoye par l'API (erreurs par champ en 422). */
export class ApiError extends Error {
  status: number;
  erreurs: Record<string, string>;

  constructor(status: number, message: string, erreurs: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.erreurs = erreurs;
  }
}

function lireCookie(nom: string): string {
  if (typeof document === "undefined") return "";
  const trouve = document.cookie.match("(^|;)\\s*" + nom + "\\s*=\\s*([^;]+)");
  return trouve ? decodeURIComponent(trouve.pop()!) : "";
}

type Options = {
  methode?: "GET" | "POST" | "PUT" | "DELETE";
  corps?: unknown;
  formData?: FormData;
};

async function requete<T>(chemin: string, options: Options = {}): Promise<T> {
  const { methode = "GET", corps, formData } = options;
  const entetes: Record<string, string> = {};

  if (methode !== "GET") {
    const jeton = lireCookie("csrftoken");
    if (jeton) entetes["X-CSRFToken"] = jeton;
  }
  if (corps !== undefined) entetes["Content-Type"] = "application/json";

  const reponse = await fetch(`${BASE}/api${chemin}`, {
    method: methode,
    credentials: "include",
    headers: entetes,
    body: formData ?? (corps !== undefined ? JSON.stringify(corps) : undefined),
  });

  if (reponse.status === 204) return undefined as T;

  const texte = await reponse.text();
  const donnees = texte ? JSON.parse(texte) : null;

  if (!reponse.ok) {
    const erreurs = donnees?.erreurs ?? {};
    const message =
      donnees?.detail ??
      Object.values(erreurs)[0] ??
      `La requête a échoué (${reponse.status}).`;
    throw new ApiError(reponse.status, String(message), erreurs);
  }
  return donnees as T;
}

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const utiles = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (!utiles.length) return "";
  return "?" + utiles.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const api = {
  // ---- Session ----
  /** Pose le cookie CSRF. A appeler une fois au demarrage de l'application. */
  amorcerCsrf: () => requete<{ detail: string }>("/auth/csrf"),
  moi: () => requete<Utilisateur>("/auth/moi"),
  connexion: (username: string, password: string) =>
    requete<Utilisateur>("/auth/connexion", { methode: "POST", corps: { username, password } }),
  deconnexion: () => requete<{ detail: string }>("/auth/deconnexion", { methode: "POST" }),

  // ---- Tableau de bord ----
  dashboard: () => requete<Dashboard>("/dashboard"),

  // ---- Renseignements ----
  feed: (p: { actif?: number; type?: string; criticite?: string; tri?: string } = {}) =>
    requete<FeedItem[]>(`/renseignements${qs(p)}`),
  actifsDuFeed: (tri = "az") => requete<ActifDuFeed[]>(`/renseignements/actifs/liste${qs({ tri })}`),
  renseignement: (id: string) => requete<RenseignementDetail>(`/renseignements/${id}`),
  marquerConsulte: (id: string) =>
    requete<{ detail: string }>(`/renseignements/${id}/consulter`, { methode: "POST" }),
  actualites: (p: { q?: string; type?: string; limite?: number } = {}) =>
    requete<Renseignement[]>(`/renseignements/actualites${qs(p)}`),

  // ---- Traitements ----
  traitements: (
    p: {
      statut?: string;
      criticite?: string;
      q?: string;
      date_debut?: string;
      date_fin?: string;
      tri?: string;
    } = {}
  ) => requete<TraitementItem[]>(`/traitements${qs(p)}`),
  compteursTraitement: () => requete<CompteursTraitement>("/traitements/compteurs"),
  /** Multipart : la cloture accepte une preuve fichier. */
  enregistrerTraitement: (idRenseignement: string, formData: FormData) =>
    requete<TraitementDetail>(`/traitements/renseignement/${idRenseignement}`, {
      methode: "POST",
      formData,
    }),
  urlPdf: (pk: number) => `${BASE}/api/traitements/${pk}/pdf`,

  // ---- Actifs ----
  actifs: (p: { q?: string; type?: string } = {}) => requete<Actif[]>(`/actifs${qs(p)}`),
  statsActifs: () => requete<StatsActifs>("/actifs/stats"),
  creerActif: (donnees: Partial<Actif> & { type: string }) =>
    requete<Actif>("/actifs", { methode: "POST", corps: donnees }),
  monterVersion: (pk: number, version: string) =>
    requete<Actif>(`/actifs/${pk}/version`, { methode: "PUT", corps: { version } }),
  retirerActif: (pk: number, purger: boolean) =>
    requete<{ detail: string }>(`/actifs/${pk}${qs({ purger })}`, { methode: "DELETE" }),
  historiqueActifs: () => requete<HistoriqueActif[]>("/actifs/historique"),
  catalogue: (q?: string) => requete<ProduitCatalogue[]>(`/actifs/catalogue${qs({ q })}`),
  referentiels: () => requete<string[]>("/actifs/referentiels"),

  // ---- Profil ----
  preferences: () => requete<Preferences>("/profil/preferences"),
  enregistrerPreferences: (p: Preferences) =>
    requete<Preferences>("/profil/preferences", { methode: "PUT", corps: p }),
};
