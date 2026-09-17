"use client";

import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import Link from "next/link";
import { gsap } from "gsap";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
import { useGSAP } from "@gsap/react";

import { CalqueAmbiance } from "./CalqueAmbiance";
import { FicheDetection } from "./FicheDetection";
import { LOGOS, VIEWBOX_LOGO, ECHELLE_LOGO } from "./logos";
import { CIBLES, CIBLE_INITIALE, ORDRE_VISITE, criticiteDe } from "./scene";
import styles from "./hero.module.css";

gsap.registerPlugin(useGSAP, MotionPathPlugin);

/* Rythme du parcours, en secondes. Un tour complet dure environ trente
   secondes : assez lent pour qu'une fiche se lise, assez vif pour qu'on
   comprenne le mecanisme en quelques stations. */
const DUREE_TRAJET = 1.05;
const DUREE_VERROU = 0.42;
const DUREE_MAINTIEN = 1.7;
/** Temps laisse a la fiche deja ouverte au chargement avant que ca bouge. */
const DUREE_MAINTIEN_INITIAL = 2.4;

type Point = { x: number; y: number };

/**
 * Point de controle d'un segment : le milieu, pousse perpendiculairement.
 *
 * Sans lui le reticule irait d'une cible a l'autre en ligne droite, ce qui
 * lit comme une interpolation. L'arc donne la trajectoire un peu flottante
 * d'un balayage qui cherche.
 */
function controle(a: Point, b: Point, sens: number): Point {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const d = Math.hypot(dx, dy) || 1;
  const amplitude = Math.min(d * 0.2, 95) * sens;
  return { x: (a.x + b.x) / 2 - (dy / d) * amplitude, y: (a.y + b.y) / 2 + (dx / d) * amplitude };
}

export function HeroDetection() {
  const refHero = useRef<HTMLElement>(null);
  const refScene = useRef<HTMLDivElement>(null);
  const refReticule = useRef<HTMLDivElement>(null);
  const refTimeline = useRef<gsap.core.Timeline | null>(null);

  /* Cible verrouillee par le parcours automatique. Initialisee a la meme
     valeur cote serveur et cote client : le premier rendu est deja une image
     composee, et l'hydratation ne corrige rien. */
  const [idVerrouille, setIdVerrouille] = useState<string | null>(CIBLE_INITIALE);
  const [survol, setSurvol] = useState<string | null>(null);
  const [taille, setTaille] = useState({ l: 0, h: 0 });
  const [reduit, setReduit] = useState(false);
  const [dansEcran, setDansEcran] = useState(true);
  const [ongletActif, setOngletActif] = useState(true);
  /* Disposition compacte : le placement des cibles est traite en CSS, mais le
     parcours a besoin de savoir lesquelles sont a l'ecran pour ne pas
     verrouiller une cible masquee. Faux au premier rendu, comme cote serveur :
     seule la timeline, construite apres montage, en depend. */
  const [compact, setCompact] = useState(false);
  /* Capacite reelle de pointage : seul un dispositif a pointeur fin et a
     survol (souris, trackpad) peut remplacer son curseur par le reticule. */
  const [pointeurFin, setPointeurFin] = useState(false);
  /* Le reticule suit la souris tant que le pointeur est dans le hero. Separe
     de `survol` (qui ne vaut que sur une cible precise) : le curseur doit
     rester sous la main partout dans le hero, pas seulement au-dessus d'une
     cible. */
  const [suiviSouris, setSuiviSouris] = useState(false);
  /* Miroir synchrone de `suiviSouris`, lu dans le nettoyage de l'effet de
     suivi : un effet ne peut pas relire un state a jour dans sa fonction de
     nettoyage, seul un ref le peut. */
  const refEnSuivi = useRef(false);
  /* Position ou le parcours automatique a ete mis en pause — c'est la qu'il
     faut ramener le reticule, sans a-coup, quand la souris quitte le hero. */
  const refPosGelee = useRef<Point | null>(null);

  /* Le survol d'une cible ou le suivi de la souris priment sur le parcours :
     la main reprend la scene. Une seule condition decide de la pause, pour
     qu'aucun des deux mecanismes ne puisse relancer le parcours pendant que
     l'autre retient la scene. */
  const idAffiche = survol ?? idVerrouille;
  const enSurveillance = survol !== null || suiviSouris;
  const anime = !reduit && dansEcran && ongletActif;

  /* --- preference systeme de mouvement reduit --- */
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const maj = () => setReduit(mq.matches);
    maj();
    mq.addEventListener("change", maj);
    return () => mq.removeEventListener("change", maj);
  }, []);

  /* --- disposition compacte : meme seuil que la feuille de style --- */
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1100px)");
    const maj = () => setCompact(mq.matches);
    maj();
    mq.addEventListener("change", maj);
    return () => mq.removeEventListener("change", maj);
  }, []);

  /* --- capacite de pointage : meme condition que le curseur personnalise en CSS --- */
  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)");
    const maj = () => setPointeurFin(mq.matches);
    maj();
    mq.addEventListener("change", maj);
    return () => mq.removeEventListener("change", maj);
  }, []);

  /* --- ne rien animer hors ecran ni onglet masque --- */
  useEffect(() => {
    const el = refHero.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setDansEcran(e.isIntersecting), { threshold: 0 });
    io.observe(el);
    const surVisibilite = () => setOngletActif(!document.hidden);
    surVisibilite();
    document.addEventListener("visibilitychange", surVisibilite);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", surVisibilite);
    };
  }, []);

  /* --- taille reelle de la scene : elle sert de repere a la trajectoire --- */
  useEffect(() => {
    const el = refScene.current;
    if (!el) return;
    const ro = new ResizeObserver(([entree]) => {
      const { width, height } = entree.contentRect;
      setTaille((t) =>
        Math.abs(t.l - width) < 2 && Math.abs(t.h - height) < 2
          ? t
          : { l: Math.round(width), h: Math.round(height) },
      );
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /* ------------------------------------------------------------------
     Parcours du reticule.

     Une seule timeline maitresse porte tout l'enchainement : deplacement,
     verrouillage, lecture du logo, maintien, relachement. C'est ce qui
     permet de la mettre en pause d'un seul appel au survol, hors ecran ou
     onglet masque — et de la reconstruire proprement au redimensionnement,
     `revertOnUpdate` remettant les styles inline a zero avant de rejouer.
     ------------------------------------------------------------------ */
  useGSAP(
    () => {
      const scene = refScene.current;
      const reticule = refReticule.current;
      if (reduit || !scene || !reticule || taille.l === 0) return;

      const position = (id: string): Point => {
        const c = CIBLES.find((x) => x.id === id);
        const p = compact && c?.compact ? c.compact : { x: c?.x ?? 0.5, y: c?.y ?? 0.5 };
        return { x: p.x * taille.l, y: p.y * taille.h };
      };
      const balayage = (id: string) =>
        scene.querySelector<HTMLElement>(`[data-cible="${id}"] [data-balayage]`);

      /* En compact, les cibles absentes de la scene sortent aussi du parcours :
         sans ca le reticule s'arreterait sur du vide pendant plusieurs secondes. */
      const parcours = compact
        ? ORDRE_VISITE.filter((id) => CIBLES.find((c) => c.id === id)?.compact)
        : [...ORDRE_VISITE];
      if (parcours.length === 0) return;

      let depart = position(parcours[0]);
      gsap.set(reticule, { x: depart.x, y: depart.y });

      // Construite en pause : sans ca, une reconstruction au redimensionnement
      // (compact, taille) relancerait toujours la lecture depuis le debut,
      // meme en plein survol ou en pleine reprise en main de la souris.
      const tl = gsap.timeline({ repeat: -1, paused: true });
      // La fiche ouverte au chargement reste lisible avant le premier trajet.
      tl.to({}, { duration: DUREE_MAINTIEN_INITIAL }).call(() => setIdVerrouille(null));

      const suite = [...parcours.slice(1), parcours[0]];
      suite.forEach((id, i) => {
        const arrivee = position(id);
        const sens = i % 2 === 0 ? 1 : -1;

        tl.to(reticule, {
          motionPath: {
            path: [depart, controle(depart, arrivee, sens), arrivee],
            curviness: 1.3,
          },
          duration: DUREE_TRAJET,
          ease: "power2.inOut",
        })
          .call(() => setIdVerrouille(id))
          // Impact du verrouillage : le reticule se resserre sur la cible.
          .fromTo(
            reticule,
            { scale: 1.5 },
            { scale: 1, duration: DUREE_VERROU, ease: "back.out(2.2)" },
          )
          // Lecture du logo, pendant le resserrement.
          .fromTo(
            balayage(id),
            { yPercent: -110, opacity: 0 },
            { yPercent: 700, opacity: 1, duration: 0.52, ease: "none" },
            "<",
          )
          .set(balayage(id), { opacity: 0 })
          .to({}, { duration: DUREE_MAINTIEN })
          .call(() => setIdVerrouille(null));

        depart = arrivee;
      });

      refTimeline.current = tl;
      if (anime && !enSurveillance) tl.play();
    },
    { scope: refHero, dependencies: [reduit, compact, taille.l, taille.h], revertOnUpdate: true },
  );

  /* Pause / reprise. Un seul endroit decide, pour qu'aucun etat ne puisse
     relancer le parcours pendant qu'un autre le retient. */
  useEffect(() => {
    const tl = refTimeline.current;
    if (!tl) return;
    if (anime && !enSurveillance) tl.play();
    else tl.pause();
  }, [anime, enSurveillance]);

  /* ------------------------------------------------------------------
     Le reticule remplace le curseur de la souris.

     Des l'entree dans le hero : le parcours automatique se fige exactement
     la ou il en etait (`refPosGelee`), et le reticule se met a suivre le
     pointeur. A la sortie, il est ramene — par un bref trajet, pas un saut —
     a cette position gelee, et seulement alors le parcours reprend : la
     reprise se raccorde exactement ou la pause avait laisse le reticule.

     Reserve aux dispositifs a pointeur fin et a survol, hors preference de
     mouvement reduit et hors disposition compacte (le reticule y est masque)
     — les trois memes conditions que le `cursor: none` de la feuille de
     style, pour que le curseur systeme ne disparaisse jamais sans un
     reticule pour le remplacer.
     ------------------------------------------------------------------ */
  useEffect(() => {
    const hero = refHero.current;
    const scene = refScene.current;
    const reticule = refReticule.current;
    const actif = pointeurFin && !reduit && !compact;
    if (!hero || !scene || !reticule || !actif) return;

    const versX = gsap.quickTo(reticule, "x", { duration: 0.35, ease: "power3" });
    const versY = gsap.quickTo(reticule, "y", { duration: 0.35, ease: "power3" });

    function deplacer(e: PointerEvent) {
      const cadre = scene!.getBoundingClientRect();
      versX(e.clientX - cadre.left);
      versY(e.clientY - cadre.top);
    }

    function surEntree(e: PointerEvent) {
      if (e.pointerType !== "mouse") return;
      refPosGelee.current = {
        x: (gsap.getProperty(reticule, "x") as number) || 0,
        y: (gsap.getProperty(reticule, "y") as number) || 0,
      };
      refTimeline.current?.pause();
      // Le parcours peut se figer en plein sursaut de verrouillage (l'impact
      // qui resserre le reticule sur une cible) : sans cette remise a plat, le
      // reticule suivrait la souris agrandi, au hasard du moment de l'entree.
      // Sans effet sur la reprise : le parcours reimpose sa propre echelle des
      // sa premiere image jouee.
      gsap.set(reticule, { scale: 1 });
      refEnSuivi.current = true;
      setSuiviSouris(true);
      deplacer(e);
    }

    function surSortie(e: PointerEvent) {
      if (e.pointerType !== "mouse") return;
      const cible = refPosGelee.current;
      if (!cible) {
        refEnSuivi.current = false;
        setSuiviSouris(false);
        return;
      }
      gsap.to(reticule, {
        x: cible.x,
        y: cible.y,
        duration: 0.5,
        ease: "power2.inOut",
        onComplete: () => {
          refEnSuivi.current = false;
          setSuiviSouris(false);
        },
      });
    }

    hero.addEventListener("pointerenter", surEntree);
    hero.addEventListener("pointermove", deplacer);
    hero.addEventListener("pointerleave", surSortie);
    return () => {
      hero.removeEventListener("pointerenter", surEntree);
      hero.removeEventListener("pointermove", deplacer);
      hero.removeEventListener("pointerleave", surSortie);
      // Si les conditions changent en plein suivi (redimensionnement franchissant
      // le seuil compact, par exemple), on rend la main au parcours automatique
      // plutot que de laisser la scene figee sur une pause orpheline.
      if (refEnSuivi.current) {
        refEnSuivi.current = false;
        setSuiviSouris(false);
      }
    };
  }, [pointeurFin, reduit, compact]);

  /* ------------------------------------------------------------------
     Placement de la fiche, mesure a l'affichage.

     L'esquisse posait « au-dessus » ou « en dessous » a la main dans la
     donnee, et une fiche de bord finissait toujours par sortir du cadre.
     Ici on mesure la boite reelle et on corrige : horizontalement par un
     decalage, verticalement par une bascule.
     ------------------------------------------------------------------ */
  useLayoutEffect(() => {
    const scene = refScene.current;
    if (!scene || !idAffiche) return;
    const fiche = scene.querySelector<HTMLElement>(`[data-cible="${idAffiche}"] [data-fiche]`);
    if (!fiche) return;

    fiche.style.setProperty("--decalage", "0px");
    fiche.removeAttribute("data-dessus");

    const cadre = scene.getBoundingClientRect();
    const boite = fiche.getBoundingClientRect();
    const marge = 12;

    let decalage = 0;
    if (boite.left < cadre.left + marge) decalage = cadre.left + marge - boite.left;
    else if (boite.right > cadre.right - marge) decalage = cadre.right - marge - boite.right;
    if (decalage !== 0) fiche.style.setProperty("--decalage", `${Math.round(decalage)}px`);

    if (boite.bottom > cadre.bottom - marge) fiche.setAttribute("data-dessus", "true");
  }, [idAffiche, taille.l, taille.h]);

  return (
    <section className={styles.hero} ref={refHero}>
      {/* Porte-filtres : le bloom est un vrai filtre SVG (deux passes de flou
          gaussien fusionnees avec la source), reference par le reticule et par
          le cadre de la cible verrouillee. */}
      <svg className={styles.defs} aria-hidden="true" focusable="false">
        <defs>
          <filter
            id="cyrens-bloom"
            x="-150%"
            y="-150%"
            width="400%"
            height="400%"
            colorInterpolationFilters="sRGB"
          >
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="proche" />
            <feGaussianBlur in="SourceGraphic" stdDeviation="5.5" result="large" />
            <feMerge>
              <feMergeNode in="large" />
              <feMergeNode in="proche" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      <CalqueAmbiance refScene={refScene} anime={anime} />

      <div className={styles.scene} ref={refScene}>
        <ul className={styles.cibles} aria-label="Exemple de périmètre surveillé">
          {CIBLES.map((cible) => (
            <li
              key={cible.id}
              className={styles.cible}
              data-cible={cible.id}
              data-criticite={criticiteDe(cible.etat)}
              data-affiche={idAffiche === cible.id}
              data-compact={cible.compact !== undefined}
              style={
                {
                  "--x": cible.x,
                  "--y": cible.y,
                  "--xm": cible.compact?.x ?? cible.x,
                  "--ym": cible.compact?.y ?? cible.y,
                } as CSSProperties
              }
              onPointerEnter={() => setSurvol(cible.id)}
              onPointerLeave={() => setSurvol((s) => (s === cible.id ? null : s))}
            >
              {/* Cadre a coins ouverts : quatre equerres, jamais un rectangle plein. */}
              <svg className={styles.cadre} viewBox="0 0 100 100" aria-hidden="true">
                <path className={styles.coin} d="M2 24 L2 2 L24 2" />
                <path className={styles.coin} d="M76 2 L98 2 L98 24" />
                <path className={styles.coin} d="M98 76 L98 98 L76 98" />
                <path className={styles.coin} d="M24 98 L2 98 L2 76" />
              </svg>

              <span className={styles.marque} aria-hidden="true">
                {cible.logo ? (
                  <svg
                    className={styles.logo}
                    viewBox={VIEWBOX_LOGO}
                    style={
                      ECHELLE_LOGO[cible.logo]
                        ? ({ transform: `scale(${ECHELLE_LOGO[cible.logo]})` } as CSSProperties)
                        : undefined
                    }
                  >
                    <path d={LOGOS[cible.logo]} />
                  </svg>
                ) : (
                  <span className={styles.sigle}>{cible.sigle ?? cible.libelle}</span>
                )}
                <span className={styles.balayageLogo} data-balayage="" />
              </span>

              <span className={styles.etiquette}>
                {cible.libelle}
                <i className={styles.version}>{cible.version}</i>
              </span>

              <FicheDetection etat={cible.etat} />

              {/* Seule surface de la scene qui capte la souris. Le cadre, le
                  logo et l'etiquette restent inertes : aucun survol ne se perd
                  sur une bordure ou un halo. */}
              <span className={styles.zone} aria-hidden="true" />
            </li>
          ))}
        </ul>

        <div className={styles.reticule} ref={refReticule} aria-hidden="true">
          <svg className={styles.reticuleSvg} viewBox="0 0 46 46">
            <path className={styles.reticuleTrait} d="M5 23 H17" />
            <path className={styles.reticuleTrait} d="M29 23 H41" />
            <path className={styles.reticuleTrait} d="M23 5 V17" />
            <path className={styles.reticuleTrait} d="M23 29 V41" />
            <circle className={styles.reticulePoint} cx="23" cy="23" r="2.6" />
          </svg>
        </div>
      </div>

      <div className={styles.copie}>
        <p className={styles.hud}>
          <span className={styles.hudPoint} aria-hidden="true" />
          {"{ SUPERVISION EN COURS }"}
        </p>

        <h1 className={styles.titre}>Supervision de Renseignement Cyber</h1>

        <p className={styles.chapo}>
          Cyrens collecte les renseignements de cybersécurité et les corrèle avec vos actifs
          technologiques et de conformité qui vous importent.
        </p>

        <div className={styles.actions}>
          <span className={styles.boutonEnveloppe}>
            {/* Halo au survol : sans lui le passage du reticule sur le bouton
                est illisible, le reticule remplaçant le curseur systeme. */}
            <span className={styles.boutonHud} aria-hidden="true">
              <span className={styles.boutonHudEntete}>[ACCÈS AU PÉRIMÈTRE]</span>
              <span className={styles.boutonHudStatut}>Créer un compte</span>
            </span>
            <Link href="/connexion" className={`${styles.bouton} ${styles.boutonPrimaire}`}>
              Inscription
            </Link>
          </span>
        </div>
      </div>
    </section>
  );
}

