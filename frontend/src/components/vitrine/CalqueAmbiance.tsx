"use client";

import { useEffect, useRef, type RefObject } from "react";
import { gsap } from "gsap";
import styles from "./hero.module.css";

/**
 * Calque d'ambiance du hero : grille, lignes de balayage, faisceau, voile et
 * vignette, peints dans un seul canvas.
 *
 * Pourquoi un canvas plutot que des div et des degrades CSS :
 *
 *   - le faisceau est compose en `lighter`, donc c'est de la lumiere additive
 *     reelle qui s'ajoute a la grille au lieu d'un calque translucide qui la
 *     recouvre ;
 *   - le voile qui assombrit le cote du texte est peint ICI, sous les cibles.
 *     En overlay il faudrait un div par-dessus toute la scene, et c'est
 *     exactement ce genre de calque qui finit par avaler le survol des cibles.
 *     Peint dans le canvas, le probleme n'existe pas ;
 *   - un seul element compose, au lieu de cinq calques animes par le moteur
 *     de rendu.
 *
 * La boucle est branchee sur `gsap.ticker`, le meme rAF que la chorregraphie
 * du hero : il n'y a qu'une seule boucle d'animation pour toute la scene.
 */

/** Secondes pour que le faisceau traverse la scene de haut en bas. */
const CYCLE_BALAYAGE = 9;
/** Demi-hauteur du faisceau, en px CSS. */
const DEMI_FAISCEAU = 95;
/** Pas de la grille, en px CSS. */
const PAS_GRILLE = 64;
/** Canal vert du faisceau — meme teinte que --h-faible. */
const TEINTE_FAISCEAU = "62, 230, 134";

type Props = {
  /** Sert a caler le voile sur le bord reel de la scene, sans constante dupliquee. */
  refScene: RefObject<HTMLElement | null>;
  /** `false` fige une image unique : hors ecran, onglet masque, ou mouvement reduit. */
  anime: boolean;
};

/** Tuile de grille, construite en pixels physiques pour rester nette. */
function tuileGrille(dpr: number): CanvasPattern | null {
  const pas = PAS_GRILLE * dpr;
  const tuile = document.createElement("canvas");
  tuile.width = pas;
  tuile.height = pas;
  const c = tuile.getContext("2d");
  if (!c) return null;
  c.fillStyle = "rgba(255, 255, 255, 0.038)";
  c.fillRect(0, 0, pas, dpr);
  c.fillRect(0, 0, dpr, pas);
  return c.createPattern(tuile, "repeat");
}

/** Tuile de lignes de balayage : une ligne claire toutes les trois. */
function tuileLignes(dpr: number): CanvasPattern | null {
  const hauteur = Math.max(3, Math.round(3 * dpr));
  const tuile = document.createElement("canvas");
  tuile.width = 1;
  tuile.height = hauteur;
  const c = tuile.getContext("2d");
  if (!c) return null;
  c.fillStyle = "rgba(255, 255, 255, 0.028)";
  c.fillRect(0, 0, 1, Math.max(1, Math.round(dpr)));
  return c.createPattern(tuile, "repeat");
}

export function CalqueAmbiance({ refScene, anime }: Props) {
  const refCanvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = refCanvas.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let largeur = 0;
    let hauteur = 0;
    let dpr = 1;
    let grille: CanvasPattern | null = null;
    let lignes: CanvasPattern | null = null;

    /* Geometrie du voile, recalculee au redimensionnement seulement. En large
       le texte est a gauche, le voile est horizontal ; sous 900px la scene
       passe en haut et le voile devient vertical. On lit la position reelle de
       la scene plutot que de redeclarer le point de bascule. */
    let voile = { vertical: false, debut: 0, fin: 0 };

    function mesurer() {
      if (!canvas || !ctx) return;
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      largeur = rect.width;
      hauteur = rect.height;
      canvas.width = Math.round(largeur * dpr);
      canvas.height = Math.round(hauteur * dpr);
      grille = tuileGrille(dpr);
      lignes = tuileLignes(dpr);

      const scene = refScene.current?.getBoundingClientRect();
      if (!scene) {
        voile = { vertical: false, debut: 0, fin: 0 };
        return;
      }
      const gauche = scene.left - rect.left;
      const bas = scene.bottom - rect.top;
      voile =
        gauche > 40
          ? { vertical: false, debut: gauche * 0.55, fin: gauche + 150 }
          : { vertical: true, debut: bas - 140, fin: bas + 130 };
    }

    /** Remplit toute la surface avec un motif, en pixels physiques. */
    function motif(m: CanvasPattern | null, alpha: number) {
      if (!ctx || !canvas || !m) return;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = alpha;
      ctx.fillStyle = m;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
    }

    function peindre(temps: number) {
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";

      ctx.fillStyle = "#06070a";
      ctx.fillRect(0, 0, largeur, hauteur);

      motif(grille, 1);

      // Faisceau — lumiere additive, pas un calque translucide.
      const avance = ((temps % CYCLE_BALAYAGE) / CYCLE_BALAYAGE) * (hauteur + DEMI_FAISCEAU * 4);
      const y = avance - DEMI_FAISCEAU * 2;
      const faisceau = ctx.createLinearGradient(0, y - DEMI_FAISCEAU, 0, y + DEMI_FAISCEAU);
      faisceau.addColorStop(0, `rgba(${TEINTE_FAISCEAU}, 0)`);
      faisceau.addColorStop(0.45, `rgba(${TEINTE_FAISCEAU}, 0.05)`);
      faisceau.addColorStop(0.5, `rgba(${TEINTE_FAISCEAU}, 0.12)`);
      faisceau.addColorStop(0.55, `rgba(${TEINTE_FAISCEAU}, 0.05)`);
      faisceau.addColorStop(1, `rgba(${TEINTE_FAISCEAU}, 0)`);
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = faisceau;
      ctx.fillRect(0, y - DEMI_FAISCEAU, largeur, DEMI_FAISCEAU * 2);
      ctx.globalCompositeOperation = "source-over";

      motif(lignes, 1);

      // Voile : le faisceau et la grille s'eteignent la ou commence le texte.
      if (voile.fin > voile.debut) {
        const d = voile.vertical
          ? ctx.createLinearGradient(0, voile.fin, 0, voile.debut)
          : ctx.createLinearGradient(voile.debut, 0, voile.fin, 0);
        d.addColorStop(0, "rgba(6, 7, 10, 0.94)");
        d.addColorStop(1, "rgba(6, 7, 10, 0)");
        ctx.fillStyle = d;
        ctx.fillRect(0, 0, largeur, hauteur);
      }

      // Vignette : ferme les bords pour que la scene ne parte pas en biseau.
      const vignette = ctx.createRadialGradient(
        largeur * 0.62,
        hauteur * 0.45,
        Math.min(largeur, hauteur) * 0.28,
        largeur * 0.62,
        hauteur * 0.45,
        Math.max(largeur, hauteur) * 0.78,
      );
      vignette.addColorStop(0, "rgba(6, 7, 10, 0)");
      vignette.addColorStop(1, "rgba(6, 7, 10, 0.72)");
      ctx.fillStyle = vignette;
      ctx.fillRect(0, 0, largeur, hauteur);
    }

    mesurer();

    const observateur = new ResizeObserver(() => {
      mesurer();
      // Redessiner tout de suite : a l'arret, sans ca, le canvas resterait vide
      // jusqu'a la prochaine reprise.
      peindre(anime ? gsap.ticker.time : CYCLE_BALAYAGE * 0.22);
    });
    observateur.observe(canvas);

    if (!anime) {
      // Image unique, faisceau pose au quart de la scene : elle se lit comme un
      // arret sur image, pas comme un rendu casse.
      peindre(CYCLE_BALAYAGE * 0.22);
      return () => observateur.disconnect();
    }

    const boucle = (temps: number) => peindre(temps);
    gsap.ticker.add(boucle);
    return () => {
      gsap.ticker.remove(boucle);
      observateur.disconnect();
    };
  }, [anime, refScene]);

  return <canvas ref={refCanvas} className={styles.ambiance} aria-hidden="true" />;
}
