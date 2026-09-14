"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import styles from "./auth.module.css";

export default function ConnexionPage() {
  const { connecter } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const soumettre = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur("");
    setEnvoi(true);
    try {
      await connecter(username, password);
      router.push("/dashboard");
    } catch (err) {
      setErreur(err instanceof ApiError ? "Identifiants incorrects." : "Impossible de se connecter — réessayez.");
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Link href="/" className={styles.brand}><span className={styles.sq}>V</span>veille</Link>
        <div className={styles.title}>Connexion</div>
        <form onSubmit={soumettre}>
          <div className={styles.field}>
            <label htmlFor="username">Nom d&apos;utilisateur</label>
            <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </div>
          <div className={styles.field}>
            <label htmlFor="password">Mot de passe</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {erreur && <div className={styles.error}>{erreur}</div>}
          <button type="submit" className={styles.submit} disabled={envoi}>
            {envoi ? "Connexion…" : "Se connecter"}
          </button>
        </form>
        <span className={styles.switch}>Pas encore de compte ? <Link href="/inscription">Créer un compte</Link></span>
      </div>
    </div>
  );
}
