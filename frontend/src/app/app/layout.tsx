// Tout le panel est derriere une authentification et affiche des donnees
// vivantes : le prerendu statique n'y a aucun sens (il figerait au build un
// contenu qui depend de la session). On force donc le rendu a la demande,
// uniquement pour ce sous-arbre (/app) — les routes publiques restent
// pre-rendables via le layout racine.
export const dynamic = "force-dynamic";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
