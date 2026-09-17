import Link from "next/link";
import styles from "./navbar.module.css";

const LIENS = [
  { href: "#solution", libelle: "Fonctionnalités" },
  { href: "#probleme", libelle: "Cas d'usage" },
  { href: "#projection", libelle: "Tarifs" },
];

export function NavBar() {
  return (
    <header className={styles.barre}>
      <Link href="/" className={styles.logo}>
        CyRens
      </Link>

      <nav className={styles.liens} aria-label="Navigation principale">
        {LIENS.map((lien) => (
          <a key={lien.href} href={lien.href} className={styles.lien}>
            {lien.libelle}
          </a>
        ))}
      </nav>

      <div className={styles.actions}>
        <Link href="/connexion" className={`${styles.bouton} ${styles.boutonInscription}`}>
          S&apos;inscrire
        </Link>
        <Link href="/connexion" className={`${styles.bouton} ${styles.boutonConnexion}`}>
          Connexion
        </Link>
      </div>
    </header>
  );
}
