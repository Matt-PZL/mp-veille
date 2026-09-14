"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "./api";

type Utilisateur = { username: string; email: string };

type AuthContextValue = {
  utilisateur: Utilisateur | null;
  pret: boolean;
  connecter: (username: string, password: string) => Promise<void>;
  inscrire: (username: string, password: string) => Promise<void>;
  deconnecter: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [pret, setPret] = useState(false);

  const chargerUtilisateur = useCallback(async () => {
    if (!getAccessToken()) {
      setUtilisateur(null);
      setPret(true);
      return;
    }
    try {
      const moi = await api.moi();
      setUtilisateur(moi);
    } catch {
      clearTokens();
      setUtilisateur(null);
    } finally {
      setPret(true);
    }
  }, []);

  useEffect(() => {
    chargerUtilisateur();
  }, [chargerUtilisateur]);

  const connecter = async (username: string, password: string) => {
    const { access, refresh } = await api.login(username, password);
    setTokens(access, refresh);
    await chargerUtilisateur();
  };

  const inscrire = async (username: string, password: string) => {
    const { access, refresh } = await api.inscription(username, password);
    setTokens(access, refresh);
    await chargerUtilisateur();
  };

  const deconnecter = () => {
    clearTokens();
    setUtilisateur(null);
  };

  return (
    <AuthContext.Provider value={{ utilisateur, pret, connecter, inscrire, deconnecter }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit etre utilise a l'interieur de <AuthProvider>");
  return ctx;
}
