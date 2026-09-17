"use client";

import { useState } from "react";
import styles from "./section.module.css";
import s from "./solution.module.css";

type Onglet = "dashboard" | "liste" | "actif" | "filtres";

const ONGLETS: { id: Onglet; libelle: string }[] = [
  { id: "dashboard", libelle: "Dashboard" },
  { id: "liste", libelle: "Renseignements" },
  { id: "actif", libelle: "Vue actif" },
  { id: "filtres", libelle: "Filtres" },
];

const RENSEIGNEMENTS = [
  { nature: "vulnerabilite", criticite: "critique", libelle: "CVE-2025-1974 · ingress-nginx", detail: "CVSS 9.8 · exploit public" },
  { nature: "correctif", criticite: "elevee", libelle: "OpenSSL 3.0.7", detail: "Correctif disponible pour CVE-2022-3602" },
  { nature: "reglementaire", criticite: "moyenne", libelle: "NIS2 · échéance J-42", detail: "Revue du périmètre · 2 mesures ouvertes" },
  { nature: "information", criticite: "faible", libelle: "CERTFR-2026-AVI-0926", detail: "Avis éditeur · noyau Linux" },
] as const;

/** Donnee de demonstration — mêmes libellés que la scène du hero. */
function CaptureDashboard() {
  return (
    <div>
      <div className={s.kpiLigne}>
        <div className={s.kpi}>
          <div className={s.kpiLabel}>Correspondances critiques</div>
          <div className={s.kpiValeur} data-teinte="critique">3</div>
        </div>
        <div className={s.kpi}>
          <div className={s.kpiLabel}>À traiter</div>
          <div className={s.kpiValeur} data-teinte="elevee">12</div>
        </div>
        <div className={s.kpi}>
          <div className={s.kpiLabel}>Actifs sains</div>
          <div className={s.kpiValeur} data-teinte="ok">86</div>
        </div>
      </div>
      {[
        { label: "Vulnérabilités", valeur: 14, total: 20, couleur: "#c9332e" },
        { label: "Correctifs", valeur: 9, total: 20, couleur: "#1b7f47" },
        { label: "Conformité", valeur: 5, total: 20, couleur: "#6d3aba" },
      ].map((b) => (
        <div key={b.label} className={s.barreLigne}>
          <span className={s.barreLabel}>{b.label}</span>
          <span className={s.barrePiste}>
            <span
              className={s.barreValeur}
              style={{ width: `${(b.valeur / b.total) * 100}%`, background: b.couleur }}
            />
          </span>
          <span className={s.barreChiffre}>{b.valeur}</span>
        </div>
      ))}
    </div>
  );
}

function CaptureListe() {
  return (
    <div>
      {RENSEIGNEMENTS.map((r) => (
        <div key={r.libelle} className={s.tableLigne}>
          <span>
            <span className={s.tableLibelle}>{r.libelle}</span>
            <span className={s.tableDetail}>{r.detail}</span>
          </span>
          <span className={s.tag} data-nature={r.nature}>
            {r.nature}
          </span>
          <span className={s.point} data-criticite={r.criticite} />
        </div>
      ))}
    </div>
  );
}

function CaptureActif() {
  return (
    <div>
      <div className={s.actifEntete}>
        <span className={s.actifPastille}>NX</span>
        <span>
          <div className={s.actifNom}>ingress-nginx</div>
          <div className={s.actifVersion}>version 1.11.4 · production</div>
        </span>
      </div>
      {RENSEIGNEMENTS.slice(0, 2).map((r) => (
        <div key={r.libelle} className={s.tableLigne} style={{ gridTemplateColumns: "1fr auto" }}>
          <span>
            <span className={s.tableLibelle}>{r.libelle}</span>
            <span className={s.tableDetail}>{r.detail}</span>
          </span>
          <span className={s.point} data-criticite={r.criticite} />
        </div>
      ))}
    </div>
  );
}

function CaptureFiltres() {
  return (
    <div>
      <div className={s.filtreGroupe}>
        <span className={s.filtreLabel}>Nature</span>
        <div className={s.puces}>
          <span className={`${s.puce} ${s.puceActive}`}>Vulnérabilité</span>
          <span className={s.puce}>Correctif</span>
          <span className={s.puce}>Réglementaire</span>
          <span className={s.puce}>Information</span>
        </div>
      </div>
      <div className={s.filtreGroupe}>
        <span className={s.filtreLabel}>Criticité</span>
        <div className={s.puces}>
          <span className={`${s.puce} ${s.puceActive}`}>Critique</span>
          <span className={`${s.puce} ${s.puceActive}`}>Élevée</span>
          <span className={s.puce}>Moyenne</span>
          <span className={s.puce}>Faible</span>
        </div>
      </div>
      <div className={s.filtreGroupe}>
        <span className={s.filtreLabel}>Périmètre</span>
        <div className={s.puces}>
          <span className={`${s.puce} ${s.puceActive}`}>Production</span>
          <span className={s.puce}>Préproduction</span>
        </div>
      </div>
    </div>
  );
}

const CAPTURES: Record<Onglet, () => React.JSX.Element> = {
  dashboard: CaptureDashboard,
  liste: CaptureListe,
  actif: CaptureActif,
  filtres: CaptureFiltres,
};

export function SectionSolution() {
  const [onglet, setOnglet] = useState<Onglet>("dashboard");
  const Capture = CAPTURES[onglet];

  return (
    <section id="solution" className={`${styles.section} ${styles.sectionDouce}`}>
      <div className={styles.conteneur}>
        <div className={s.grille}>
          <div>
            <p className={styles.oeil}>{"{ LA SOLUTION }"}</p>
            <h2 className={styles.titre}>Un seul flux, corrélé à ce que vous exploitez réellement</h2>
            <p className={styles.chapo}>
              Cyrens collecte les renseignements publiés, les confronte à votre parc technique et
              normatif, puis ne remonte que les correspondances qui vous concernent — avec la
              référence source, la criticité et le contexte pour agir tout de suite.
            </p>
            <ol className={s.etapes}>
              <li className={s.etape}>
                <span className={s.etapeChiffre}>1</span>
                <span className={s.etapeTexte}>
                  <strong>Collecte</strong> continue des renseignements cyber et des textes de
                  conformité.
                </span>
              </li>
              <li className={s.etape}>
                <span className={s.etapeChiffre}>2</span>
                <span className={s.etapeTexte}>
                  <strong>Corrélation</strong> automatique avec vos actifs techniques et vos
                  référentiels normatifs.
                </span>
              </li>
              <li className={s.etape}>
                <span className={s.etapeChiffre}>3</span>
                <span className={s.etapeTexte}>
                  <strong>Traitement</strong> priorisé, historisé et exportable pour vos audits.
                </span>
              </li>
            </ol>

            <a href="/connexion" className={styles.ctaBouton}>
              Demander une démonstration
            </a>
          </div>

          <div className={s.cadre}>
            <div className={s.cadreBarre}>
              <span className={s.cadrePoint} />
              <span className={s.cadrePoint} />
              <span className={s.cadrePoint} />
              <div className={s.onglets}>
                {ONGLETS.map((o) => (
                  <button
                    key={o.id}
                    type="button"
                    className={`${s.onglet} ${onglet === o.id ? s.ongletActif : ""}`}
                    onClick={() => setOnglet(o.id)}
                  >
                    {o.libelle}
                  </button>
                ))}
              </div>
            </div>
            <div className={s.capture}>
              <Capture />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
