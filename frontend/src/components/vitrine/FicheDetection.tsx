import type { EtatCible } from "./scene";
import styles from "./hero.module.css";

/**
 * Fiche HUD affichee sous une cible verrouillee.
 *
 * Elle reste du DOM, et pas un rendu graphique : ce sont des references de
 * renseignements verifiables, elles doivent etre selectionnables, lisibles par
 * un lecteur d'ecran et indexables.
 *
 * Le halo neon est un duplicata du texte reellement floute (`filter: blur`)
 * compose en `screen` derriere le glyphe net — un bloom, pas un empilement de
 * `text-shadow` qui ne ferait qu'epaissir le contour.
 */

const ENTETE = "[DÉTECTION DE RENSEIGNEMENTS]";

/** Libelle + halo. Le duplicata est masque aux technologies d'assistance. */
function Statut({ texte, analyse = false }: { texte: string; analyse?: boolean }) {
  return (
    <span className={styles.ficheStatut}>
      <span className={styles.statutHalo} aria-hidden="true">
        {texte}
      </span>
      {texte}
      {analyse ? <span className={styles.pointAnalyse} aria-hidden="true" /> : null}
    </span>
  );
}

export function FicheDetection({ etat }: { etat: EtatCible }) {
  return (
    <div className={styles.fiche} data-fiche="">
      {/* Chrome visuel du HUD : repete dix fois, il n'apporte rien a l'oral. */}
      <div className={styles.ficheEntete} aria-hidden="true">
        {ENTETE}
      </div>

      {etat.code === "ras" ? (
        <>
          <Statut texte="RAS" />
          <span className={styles.ficheDetail}>Aucun renseignement actif</span>
        </>
      ) : null}

      {etat.code === "analyse" ? (
        <>
          <Statut texte="ANALYSE" analyse />
          <span className={styles.ficheDetail}>Corrélation en cours</span>
        </>
      ) : null}

      {etat.code === "correspondance" ? (
        <>
          <Statut texte={etat.libelle} />
          <span className={styles.ficheDetail}>
            {etat.detail}
            <span className={styles.ficheSource}>source · {etat.source}</span>
          </span>
        </>
      ) : null}
    </div>
  );
}
