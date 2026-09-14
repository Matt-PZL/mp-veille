"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import styles from "./AppNav.module.css";

const DJANGO_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Liens vers les pages pas encore migrees : elles restent servies par
 * l'app Django existante le temps de la transition, cote a cote avec
 * les pages deja portees sur Next.js. */
const PAGES_HERITEES = [
  { href: `${DJANGO_URL}/renseignements/`, label: "Renseignements" },
  { href: `${DJANGO_URL}/traitement/`, label: "Traitement" },
  { href: `${DJANGO_URL}/actifs/`, label: "Gestion des actifs" },
  { href: `${DJANGO_URL}/actualites/`, label: "Actualités" },
];

export default function AppNav() {
  const { utilisateur, deconnecter } = useAuth();

  return (
    <nav className={styles.topbar}>
      <Link href="/dashboard" className={styles.brand}>
        <span className={styles.sq}>V</span>veille
      </Link>
      <div className={styles.links}>
        <Link href="/dashboard" className={`${styles.link} ${styles.active}`}>Tableau de bord</Link>
        {PAGES_HERITEES.map((p) => (
          <a key={p.href} href={p.href} className={styles.link}>
            {p.label}<span className={styles.legacyBadge}>v1</span>
          </a>
        ))}
      </div>
      <div className={styles.right}>
        {utilisateur && <span className={styles.user}>{utilisateur.username}</span>}
        <button className={styles.logout} onClick={deconnecter}>Se déconnecter</button>
      </div>
    </nav>
  );
}
