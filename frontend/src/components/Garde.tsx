"use client";

/**
 * Garde d'authentification.
 *
 * Attend que /auth/moi ait repondu avant de decider : sans cette attente,
 * un simple rafraichissement renverrait vers la connexion alors que la
 * session est valide (le cookie est httpOnly, donc invisible au JS).
 */

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { Spinner } from "./ui";

export function Garde({ children }: { children: React.ReactNode }) {
  const { utilisateur, chargement } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!chargement && !utilisateur) router.replace("/connexion");
  }, [chargement, utilisateur, router]);

  if (chargement) return <Spinner texte="Vérification de la session…" />;
  if (!utilisateur) return null;
  return <>{children}</>;
}
