import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Le VM est accedee par son IP LAN (192.168.1.24), pas juste localhost :
  // sans ca, Next.js bloque ses propres ressources de dev (HMR) venant de cette origine.
  allowedDevOrigins: ["192.168.1.24"],
  // Produit un serveur autonome dans .next/standalone : l'image de production
  // n'embarque que les dependances reellement utilisees, au lieu de tout
  // node_modules.
  output: "standalone",

  // Le front et l'API tournent sur des ports differents du meme hote LAN.
  // Un fetch() cote navigateur vers une IP privee declenche les protections
  // "Private Network Access" de Chrome/Edge (bloque en silence, ou popup de
  // permission selon la version) : deux sources d'echec impossibles a
  // garantir cote client. On evite tout ca en ne faisant jamais parler le
  // navigateur qu'a sa propre origine (ce meme port) : c'est le serveur
  // Next.js qui relaie vers Django, en requete serveur-a-serveur, hors de
  // portee de ces protections navigateur.
  async rewrites() {
    const cible = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [{ source: "/api/:chemin*", destination: `${cible}/api/:chemin*` }];
  },
};

export default nextConfig;
