"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

/** Redirige vers /login si personne n'est connecte, une fois le contexte
 * d'auth pret (evite un flash de contenu protege avant verification). */
export default function ProtegePage({ children }: { children: React.ReactNode }) {
  const { utilisateur, pret } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (pret && !utilisateur) router.replace("/login");
  }, [pret, utilisateur, router]);

  if (!pret || !utilisateur) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-faint)", fontSize: 13 }}>
        Chargement…
      </div>
    );
  }

  return <>{children}</>;
}
