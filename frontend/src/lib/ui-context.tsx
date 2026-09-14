"use client";

/**
 * Preferences d'interface : theme, accent, et disposition de la navigation.
 *
 * Toutes vivent dans le navigateur et sont posees en attributs sur <html> —
 * le CSS fait le reste via ses tokens, aucun composant n'a a connaitre l'etat
 * courant. Un script inline dans le layout les applique AVANT le premier
 * rendu, sinon on verrait un clignotement (theme sombre puis clair, nav
 * horizontale puis verticale) a chaque chargement de page.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Mode = "dark" | "light";
export type Accent = "bleu" | "vert" | "violet";
/** "horizontale" = onglets en haut ; "verticale" = tiroir lateral au clic. */
export type Nav = "horizontale" | "verticale";

type Contexte = {
  mode: Mode;
  accent: Accent;
  nav: Nav;
  basculerMode: () => void;
  choisirAccent: (a: Accent) => void;
  choisirNav: (n: Nav) => void;
};

const UiContext = createContext<Contexte | null>(null);

/** Cles de stockage — partagees avec le script inline du layout. */
export const CLES = {
  mode: "veille-mode",
  accent: "veille-accent",
  nav: "veille-nav",
} as const;

function lire<T extends string>(cle: string, defaut: T): T {
  try {
    return (localStorage.getItem(cle) as T) || defaut;
  } catch {
    return defaut;
  }
}

function ecrire(cle: string, valeur: string) {
  try {
    localStorage.setItem(cle, valeur);
  } catch {
    /* stockage indisponible (navigation privee) : la preference vaut pour la session */
  }
}

export function UiProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<Mode>("dark");
  const [accent, setAccent] = useState<Accent>("bleu");
  const [nav, setNav] = useState<Nav>("horizontale");

  // Le script inline a deja applique les attributs ; on se contente ici de
  // synchroniser l'etat React avec ce qui est deja affiche.
  useEffect(() => {
    setMode(lire<Mode>(CLES.mode, "dark"));
    setAccent(lire<Accent>(CLES.accent, "bleu"));
    setNav(lire<Nav>(CLES.nav, "horizontale"));
  }, []);

  useEffect(() => {
    const r = document.documentElement;
    r.setAttribute("data-theme", mode);
    r.setAttribute("data-accent", accent);
    r.setAttribute("data-nav", nav);
  }, [mode, accent, nav]);

  const basculerMode = useCallback(() => {
    setMode((p) => {
      const s = p === "dark" ? "light" : "dark";
      ecrire(CLES.mode, s);
      return s;
    });
  }, []);

  const choisirAccent = useCallback((a: Accent) => {
    setAccent(a);
    ecrire(CLES.accent, a);
  }, []);

  const choisirNav = useCallback((n: Nav) => {
    setNav(n);
    ecrire(CLES.nav, n);
  }, []);

  return (
    <UiContext.Provider
      value={{ mode, accent, nav, basculerMode, choisirAccent, choisirNav }}
    >
      {children}
    </UiContext.Provider>
  );
}

export function useUi(): Contexte {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error("useUi doit être utilisé dans un UiProvider.");
  return ctx;
}
