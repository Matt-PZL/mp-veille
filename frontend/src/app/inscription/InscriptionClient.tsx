"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import styles from "../login/auth.module.css";

export default function InscriptionPage() {
  const { inscrire } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const soumettre = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur("");
    if (password !== confirmation) {
      setErreur("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setEnvoi(true);
    try {
      await inscrire(username, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.detail && typeof err.detail === "object") {
        const premiere = Object.values(err.detail as Record<string, string[]>)[0];
        setErreur(Array.isArray(premiere) ? premiere[0] : "Inscription impossible.");
      } else {
        setErreur("Inscription impossible — réessayez.");
      }
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Link href="/" className={styles.brand}><span className={styles.sq}>V</span>veille</Link>
        <div className={styles.title}>Créer un compte</div>
        <form onSubmit={soumettre}>
          <div className={styles.field}>
            <label htmlFor="username">Nom d&apos;utilisateur</label>
            <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </div>
          <div className={styles.field}>
            <label htmlFor="password">Mot de passe</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div className={styles.field}>
            <label htmlFor="confirmation">Confirmer le mot de passe</label>
            <input id="confirmation" type="password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} required />
          </div>
          {erreur && <div className={styles.error}>{erreur}</div>}
          <button type="submit" className={styles.submit} disabled={envoi}>
            {envoi ? "Création…" : "Créer mon compte"}
          </button>
        </form>
        <span className={styles.switch}>Déjà un compte ? <Link href="/login">Se connecter</Link></span>
      </div>
    </div>
  );
}
