/** Formatage partage — toujours en francais, comme le reste du produit. */

export function depuis(iso: string | null): string {
  if (!iso) return "—";
  const secondes = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  const paliers: [number, string, string][] = [
    [60, "seconde", "secondes"],
    [3600, "minute", "minutes"],
    [86400, "heure", "heures"],
    [2592000, "jour", "jours"],
    [31536000, "mois", "mois"],
    [Infinity, "an", "ans"],
  ];
  const diviseurs = [1, 60, 3600, 86400, 2592000, 31536000];
  for (let i = 0; i < paliers.length; i++) {
    if (secondes < paliers[i][0]) {
      const n = Math.floor(secondes / diviseurs[i]);
      return `${n} ${n > 1 ? paliers[i][2] : paliers[i][1]}`;
    }
  }
  return "—";
}

export function dateCourte(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}

export function dateLongue(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function pluriel(n: number, singulier = "", pluriel = "s"): string {
  return n > 1 ? pluriel : singulier;
}

export function tronquer(texte: string, n: number): string {
  return texte.length <= n ? texte : texte.slice(0, n).trimEnd() + "…";
}
