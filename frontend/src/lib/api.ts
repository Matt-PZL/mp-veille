/**
 * Client API — appelle le backend Django (apps.api, DRF + JWT).
 *
 * Stockage du token en localStorage pour cette premiere passe de migration :
 * simple et suffisant pour demarrer, mais pas le choix le plus dur en
 * securite pour une vraie prod (un cookie httpOnly + refresh cote serveur
 * serait la prochaine etape de durcissement — cf. README du frontend).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "veille_access_token";
const REFRESH_KEY = "veille_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  window.localStorage.setItem(TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "Erreur API");
    this.status = status;
    this.detail = detail;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  const res = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = await res.json();
  window.localStorage.setItem(TOKEN_KEY, data.access);
  return data.access as string;
}

/** Appelle l'API. Rejoue automatiquement une fois avec un token rafraichi
 * si l'access token a expire (401). */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const doFetch = async (token: string | null) => {
    const finalHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...(headers as Record<string, string> | undefined),
    };
    if (auth && token) finalHeaders["Authorization"] = `Bearer ${token}`;
    return fetch(`${API_URL}${path}`, { ...rest, headers: finalHeaders });
  };

  let res = await doFetch(getAccessToken());

  if (res.status === 401 && auth) {
    const nouveauToken = await refreshAccessToken();
    if (nouveauToken) res = await doFetch(nouveauToken);
  }

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- Endpoints typés -------------------------------------------------

export type Dashboard = {
  nb_total_renseignements: number;
  nb_actifs: number;
  par_criticite: Record<string, number>;
  par_etape: Record<string, number>;
  non_consultes_count: number;
  taux_cloture: number | null;
  total_traitements: number;
  actifs_sans_renseignement: string[];
  en_retard: unknown[];
  echeances_a_venir: unknown[];
  prioritaires: Renseignement[];
  derniers_renseignements: Renseignement[];
};

export type Renseignement = {
  id_renseignement_bdp: string;
  type: string;
  type_display: string;
  titre: string;
  description: string;
  source: string;
  url_source: string;
  reference_courte: string;
  criticite: string;
  criticite_display: string;
  nature: string;
  nature_display: string;
  cvss_score: number | null;
  cvss_vector: string;
  decouvert_le: string;
  statut: string;
  statut_display: string;
  actif_lie: string | null;
};

export type ActifClient = {
  id: number;
  type: string;
  type_display: string;
  categorie: string;
  editeur: string;
  produit: string;
  version: string;
  referentiel: string;
  nb_traitements: number;
  couvert: boolean;
};

export const api = {
  login: (username: string, password: string) =>
    apiFetch<{ access: string; refresh: string }>("/api/auth/token/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username, password }),
    }),
  inscription: (username: string, password: string) =>
    apiFetch<{ access: string; refresh: string; username: string }>("/api/auth/inscription/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username, password }),
    }),
  moi: () => apiFetch<{ username: string; email: string }>("/api/auth/moi/"),
  dashboard: () => apiFetch<Dashboard>("/api/dashboard/"),
  renseignements: (params: Record<string, string> = {}) =>
    apiFetch<{ count: number; results: Renseignement[] }>(
      `/api/renseignements/?${new URLSearchParams(params)}`
    ),
  actifs: () =>
    apiFetch<{ count: number; results: ActifClient[]; historique: unknown[] }>("/api/actifs/"),
  catalogue: (q: string) =>
    apiFetch<{ id: number; categorie: string; editeur: string; produit: string }[]>(
      `/api/catalogue/?q=${encodeURIComponent(q)}`
    ),
  contact: (data: { nom: string; email: string; entreprise?: string; message: string }) =>
    apiFetch<{ ok: true }>("/api/contact/", { method: "POST", auth: false, body: JSON.stringify(data) }),
};
