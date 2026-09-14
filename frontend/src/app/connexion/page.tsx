"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button, ErreurChamp, Input, Label } from "@/components/ui";

export default function PageConnexion() {
  const { utilisateur, chargement, connexion } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!chargement && utilisateur) router.replace("/");
  }, [chargement, utilisateur, router]);

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setErreur(null);
    setEnvoi(true);
    try {
      await connexion(username, password);
      router.replace("/");
    } catch (err) {
      setErreur(err instanceof Error ? err.message : "La connexion a échoué.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-[18px]">
      <div className="w-full max-w-[400px] rounded-2xl border border-border bg-surface px-8 py-[34px] shadow-pop">
        <div className="mb-2 flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-[10px] bg-accent font-display text-base font-extrabold text-accent-ink">
            V
          </span>
          <span className="font-display text-[17px] font-bold tracking-tight">veille</span>
        </div>
        <p className="mb-6 text-[13px] text-ink-faint">
          Veille cyber &amp; normative — connectez-vous pour continuer.
        </p>

        <form onSubmit={soumettre}>
          {erreur && <p className="mb-4 text-[12.5px] font-semibold text-crit">{erreur}</p>}

          <div className="mb-4">
            <Label>Nom d&apos;utilisateur</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="mb-4">
            <Label>Mot de passe</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <ErreurChamp />
          <Button type="submit" variante="primaire" disabled={envoi} className="mt-2 w-full py-2.5">
            {envoi ? "Connexion…" : "Se connecter"}
          </Button>
        </form>
      </div>
    </div>
  );
}
