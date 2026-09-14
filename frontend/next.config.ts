import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Produit un serveur autonome dans .next/standalone : l'image de production
  // n'embarque que les dependances reellement utilisees, au lieu de tout
  // node_modules.
  output: "standalone",
};

export default nextConfig;
