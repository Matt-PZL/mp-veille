import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import { UiProvider } from "@/lib/ui-context";
import "./globals.css";

// next/font heberge les polices avec l'application : pas de <head> manuel,
// pas de requete vers Google au chargement, et aucun decalage de texte au
// premier rendu.
const archivo = Archivo({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-archivo",
  display: "swap",
});
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

// Le rendu a la demande (force-dynamic) ne concerne que le panel
// authentifie : il est declare dans app/app/layout.tsx, pas ici, pour que
// les routes publiques (site vitrine, connexion) restent pre-rendables.
export const metadata: Metadata = {
  title: "Veille — cyber & normative",
  description: "Panel de veille sur vos actifs techniques et vos référentiels normatifs.",
};

/**
 * Applique les preferences AVANT le premier rendu.
 *
 * Sans ce script, chaque chargement afficherait brievement les valeurs par
 * defaut (sombre, nav horizontale) avant que React ne lise le stockage local
 * dans un effet — soit un clignotement visible a chaque navigation.
 * Volontairement minimal et tolerant : si le stockage est indisponible
 * (navigation privee), on garde les defauts sans casser la page.
 */
const SCRIPT_PREFERENCES = `
(function(){
  try{
    var r = document.documentElement;
    r.setAttribute('data-theme',  localStorage.getItem('veille-mode')   || 'dark');
    r.setAttribute('data-accent', localStorage.getItem('veille-accent') || 'bleu');
    r.setAttribute('data-nav',    localStorage.getItem('veille-nav')    || 'horizontale');
  }catch(e){}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="fr"
      data-theme="dark"
      data-accent="bleu"
      data-nav="horizontale"
      className={`${archivo.variable} ${plexSans.variable} ${plexMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_PREFERENCES }} />
        <UiProvider>
          <AuthProvider>{children}</AuthProvider>
        </UiProvider>
      </body>
    </html>
  );
}
