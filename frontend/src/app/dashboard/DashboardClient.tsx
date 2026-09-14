"use client";

import { useEffect, useState } from "react";
import ProtegePage from "@/components/ProtegePage";
import AppNav from "@/components/AppNav";
import styles from "./dashboard.module.css";
import navStyles from "@/components/AppNav.module.css";
import { api, ApiError, type Dashboard } from "@/lib/api";

function DashboardContenu() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => {
      setErreur(e instanceof ApiError ? "Impossible de charger le tableau de bord." : "Erreur réseau.");
    });
  }, []);

  if (erreur) return <div className={styles.errBox}>{erreur}</div>;
  if (!data) return <div className={styles.loading}>Chargement du tableau de bord…</div>;

  return (
    <>
      <div className={styles.header}>
        <h1 className={styles.title}>Vue d&apos;ensemble</h1>
      </div>
      <p className={styles.sub}>
        <b>{data.nb_total_renseignements}</b> renseignements suivis sur <b>{data.nb_actifs}</b> actifs/référentiels déclarés.
      </p>

      <div className={styles.kpis}>
        <div className={`${styles.kpi} red`}>
          <div className={styles.kpiLbl}>Critiques</div>
          <div className={styles.kpiVal}>{data.par_criticite.critique ?? 0}</div>
        </div>
        <div className={`${styles.kpi} orange`}>
          <div className={styles.kpiLbl}>Élevées</div>
          <div className={styles.kpiVal}>{data.par_criticite.elevee ?? 0}</div>
        </div>
        <div className={`${styles.kpi} blue`}>
          <div className={styles.kpiLbl}>Non consultés</div>
          <div className={styles.kpiVal}>{data.non_consultes_count}</div>
        </div>
        <div className={`${styles.kpi} violet`}>
          <div className={styles.kpiLbl}>Traitements clos</div>
          <div className={styles.kpiVal}>{data.taux_cloture ?? 0}%</div>
        </div>
      </div>

      <div className={styles.row2}>
        <div className={styles.card}>
          <div className={styles.cardHead}>Renseignements prioritaires</div>
          {data.prioritaires.length === 0 && <div className={styles.empty}>Aucun renseignement à prioriser.</div>}
          {data.prioritaires.map((r) => (
            <div className={styles.item} key={r.id_renseignement_bdp}>
              <span className={styles.itemTitle}>
                <span className={`${styles.dot} ${r.criticite}`} />
                {r.reference_courte || r.source} — {r.titre}
              </span>
              <span className={styles.meta}>{r.statut_display}</span>
            </div>
          ))}
        </div>
        <div className={styles.card}>
          <div className={styles.cardHead}>Derniers renseignements</div>
          {data.derniers_renseignements.length === 0 && <div className={styles.empty}>Aucun renseignement pour le moment.</div>}
          {data.derniers_renseignements.map((r) => (
            <div className={styles.item} key={r.id_renseignement_bdp}>
              <span className={styles.itemTitle}>
                <span className={`${styles.dot} ${r.criticite}`} />
                {r.reference_courte || r.source} — {r.titre}
              </span>
              <span className={navStyles.legacyBadge}>{r.type_display}</span>
            </div>
          ))}
        </div>
      </div>

      {data.actifs_sans_renseignement.length > 0 && (
        <div className={styles.card}>
          <div className={styles.cardHead}>Actifs non couverts par une source</div>
          {data.actifs_sans_renseignement.map((nom) => (
            <div className={styles.item} key={nom}>
              <span className={styles.itemTitle}>{nom}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default function DashboardPage() {
  return (
    <ProtegePage>
      <AppNav />
      <div className={navStyles.content}>
        <DashboardContenu />
      </div>
    </ProtegePage>
  );
}
