import { IconShield, IconTarget, IconClipboard } from "@/components/icons";
import styles from "./section.module.css";

const CARTES = [
  {
    teinte: "critique" as const,
    icone: IconShield,
    titre: "Vulnérabilités",
    items: ["Nouvelles CVE chaque jour", "Correctifs", "Bulletins de sécurité"],
  },
  {
    teinte: "elevee" as const,
    icone: IconTarget,
    titre: "Menaces",
    items: ["IOC", "Campagnes", "Leaks", "Alertes"],
  },
  {
    teinte: "normatif" as const,
    icone: IconClipboard,
    titre: "Conformité",
    items: ["NIS2", "DORA", "RGPD", "ISO 27001"],
  },
];

export function SectionProbleme() {
  return (
    <section id="probleme" className={styles.section}>
      <div className={styles.conteneur}>
        <div className={`${styles.entete} ${styles.centre}`}>
          <p className={styles.oeil}>{"{ LE PROBLÈME }"}</p>
          <h2 className={styles.titre}>La veille cyber classique noie plus qu&apos;elle n&apos;informe</h2>
          <p className={styles.chapo}>
            Flux dispersés, alertes non triées, correctifs à recouper manuellement avec le parc :
            les équipes cyber passent plus de temps à trier la veille qu&apos;à agir dessus — sans
            jamais être sûres de ne rien avoir manqué sur leurs actifs réels.
          </p>
        </div>

        <div className={styles.grille3}>
          {CARTES.map((carte) => (
            <div key={carte.titre} className={styles.carte}>
              <span className={styles.carteIcone} data-teinte={carte.teinte}>
                <carte.icone />
              </span>
              <h3 className={styles.carteTitre}>{carte.titre}</h3>
              <ul className={styles.carteListe}>
                {carte.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div style={{ textAlign: "center" }}>
          <a href="#solution" className={styles.cta}>
            Voir comment Cyrens corrige ça
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </a>
        </div>
      </div>
    </section>
  );
}
