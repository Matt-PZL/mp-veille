import { IconCheck, IconBars, IconClock, IconRefresh } from "@/components/icons";
import { LOGOS, VIEWBOX_LOGO, ECHELLE_LOGO, type CleLogo } from "./logos";
import styles from "./section.module.css";
import p from "./projection.module.css";

const TECHNOLOGIES: { libelle: string; logo: CleLogo | null; sigle?: string }[] = [
  { libelle: "Windows", logo: "windows" },
  { libelle: "OpenSSH", logo: null, sigle: "SSH" },
  { libelle: "Apache", logo: "apache" },
  { libelle: "VMware", logo: "vmware" },
  { libelle: "PostgreSQL", logo: "postgresql" },
  { libelle: "Cisco", logo: "cisco" },
];

const REFERENTIELS = ["NIS2", "DORA", "RGPD", "ISO 27001", "ISO 27002"];

const BENEFICES = [
  {
    icone: IconCheck,
    titre: "Réduire les faux positifs",
    texte: "Seules les correspondances confirmées avec votre parc réel remontent.",
  },
  {
    icone: IconBars,
    titre: "Prioriser les risques",
    texte: "Criticité et exploitabilité classées pour traiter l'essentiel en premier.",
  },
  {
    icone: IconClock,
    titre: "Gagner du temps",
    texte: "Le tri manuel des flux de veille disparaît du quotidien des équipes.",
  },
  {
    icone: IconRefresh,
    titre: "Réactivité",
    texte: "Une correspondance critique est visible dès sa publication.",
  },
];

export function SectionProjection() {
  return (
    <section id="projection" className={styles.section}>
      <div className={styles.conteneur}>
        <div className={`${styles.entete} ${styles.centre}`}>
          <p className={styles.oeil}>{"{ VOTRE PÉRIMÈTRE }"}</p>
          <h2 className={styles.titre}>Pensé pour votre parc, pas pour un parc générique</h2>
          <p className={styles.chapo}>
            Cyrens suit les technologies réellement déployées chez vous et les référentiels de
            conformité qui vous engagent.
          </p>
        </div>

        <div className={p.grille}>
          <div>
            <p className={p.colonneTitre}>Technologies suivies</p>
            <div className={p.logoGrille}>
              {TECHNOLOGIES.map((t) => (
                <div key={t.libelle} className={p.logoTuile}>
                  {t.logo ? (
                    <svg
                      viewBox={VIEWBOX_LOGO}
                      style={ECHELLE_LOGO[t.logo] ? { transform: `scale(${ECHELLE_LOGO[t.logo]})` } : undefined}
                    >
                      <path d={LOGOS[t.logo]} />
                    </svg>
                  ) : (
                    <span className={p.sigle}>{t.sigle}</span>
                  )}
                  <span className={p.logoTuileTexte}>{t.libelle}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className={p.colonneTitre}>Référentiels de conformité</p>
            <div className={p.badgeGrille}>
              {REFERENTIELS.map((r) => (
                <span key={r} className={p.badge}>
                  {r}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className={p.beneficesGrille}>
          {BENEFICES.map((b) => (
            <div key={b.titre} className={p.benefice}>
              <span className={p.beneficeIcone}>
                <b.icone />
              </span>
              <h3 className={p.beneficeTitre}>{b.titre}</h3>
              <p className={p.beneficeTexte}>{b.texte}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
