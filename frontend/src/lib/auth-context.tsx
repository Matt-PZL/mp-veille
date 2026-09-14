"use client";

/**
 * Session courante.
 *
 * Le cookie de session est httpOnly : le JavaScript ne peut pas le lire, donc
 * on ne peut pas deviner l'etat connecte sans demander au serveur. D'ou
 * l'appel a /auth/moi au montage, et l'etat `chargement` tant qu'il n'a pas
 * repondu — sans lui, l'application redirigerait vers la connexion a chaque
 * rafraichissement de page.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";
import type { Utilisateur } from "./types";

type Contexte = {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connexion: (username: string, password: string) => Promise<void>;
  deconnexion: () => Promise<void>;
};

const AuthContext = createContext<Contexte | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    let annule = false;
    (async () => {
      try {
        await api.amorcerCsrf();
        const u = await api.moi();
        if (!annule) setUtilisateur(u);
      } catch {
        if (!annule) setUtilisateur(null);
      } finally {
        if (!annule) setChargement(false);
      }
    })();
    return () => {
      annule = true;
    };
  }, []);

  const connexion = useCallback(async (username: string, password: string) => {
    await api.amorcerCsrf();
    setUtilisateur(await api.connexion(username, password));
  }, []);

  const deconnexion = useCallback(async () => {
    await api.deconnexion();
    setUtilisateur(null);
  }, []);

  return (
    <AuthContext.Provider value={{ utilisateur, chargement, connexion, deconnexion }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): Contexte {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un AuthProvider.");
  return ctx;
}
