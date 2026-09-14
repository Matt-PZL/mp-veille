"use client";

/**
 * Primitives d'interface partagees.
 *
 * Elles portent la meme grammaire visuelle que le panel Django : cartes a
 * coins arrondis, pastilles, points de severite a halo, chiffres en mono
 * tabulaire. Un composant ne connait jamais une couleur en dur — tout passe
 * par les tokens de globals.css.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { Criticite, Statut } from "@/lib/types";
import { IconCheck, IconChevron, IconClose } from "./icons";

/* -------------------------------------------------------------------------
   Severite
   ------------------------------------------------------------------------- */
const HALO: Record<string, string> = {
  critique: "bg-crit shadow-[0_0_0_3px_var(--color-crit-soft)]",
  elevee: "bg-elev shadow-[0_0_0_3px_var(--color-elev-soft)]",
  moyenne: "bg-moy shadow-[0_0_0_3px_var(--color-moy-soft)]",
  faible: "bg-faib shadow-[0_0_0_3px_var(--color-faib-soft)]",
};

export function SevDot({ criticite }: { criticite: Criticite }) {
  return (
    <span
      className={`size-[7px] shrink-0 rounded-full ${HALO[criticite] ?? "bg-ink-faint"}`}
      aria-hidden="true"
    />
  );
}

export const TEXTE_SEV: Record<string, string> = {
  critique: "text-crit",
  elevee: "text-elev",
  moyenne: "text-moy",
  faible: "text-faib",
};

/* -------------------------------------------------------------------------
   Pastilles
   ------------------------------------------------------------------------- */
// Couleurs de statut fixes (pas l'accent personnalisable) : "Demarre" doit
// rester bleu, "À traiter" orange, quel que soit le theme d'accent choisi.
const STATUT_STYLE: Record<Statut, string> = {
  a_traiter: "bg-gold-soft text-gold border-gold",
  en_cours: "bg-statut-demarre-soft text-statut-demarre border-statut-demarre",
  clos: "bg-faib-soft text-faib border-transparent",
  non_applicable: "bg-surface-3 text-ink-faint border-transparent",
};

export function StatusPill({ statut, label }: { statut: Statut; label: string }) {
  return (
    <span
      className={`inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-[2.5px] text-[11px] font-semibold ${STATUT_STYLE[statut]}`}
    >
      {label}
    </span>
  );
}

const NATURE_STYLE: Record<string, string> = {
  vulnerabilite: "bg-crit-soft text-crit",
  correctif: "bg-faib-soft text-faib",
  reglementaire: "bg-violet-soft text-violet",
  information: "bg-surface-3 text-ink-faint",
};

export function NatureTag({ nature, label }: { nature: string; label: string }) {
  if (!label) return null;
  return (
    <span
      className={`inline-flex items-center rounded-[5px] px-2 py-[2.5px] text-[10px] font-bold tracking-[0.05em] uppercase ${NATURE_STYLE[nature] ?? "bg-surface-3 text-ink-faint"}`}
    >
      {label}
    </span>
  );
}

/** Palier de correspondance du Matching : dit pourquoi l'item est remonte. */
export function ConfBar({ palier, pourcent }: { palier: string; pourcent: number }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 font-mono text-[10.5px] text-ink-faint"
      title={`Pourquoi ce renseignement vous est remonté : correspondance « ${palier} » avec un de vos actifs.`}
    >
      {palier}
      <span className="h-1 w-[34px] overflow-hidden rounded-full bg-surface-3">
        <span className="block h-full rounded-full bg-accent" style={{ width: `${pourcent}%` }} />
      </span>
    </span>
  );
}

/* -------------------------------------------------------------------------
   Boutons et filtres
   ------------------------------------------------------------------------- */
type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "neutre" | "primaire" | "danger";
};

export function Button({ variante = "neutre", className = "", ...props }: BtnProps) {
  const styles = {
    neutre:
      "bg-surface-2 border-border text-ink-soft hover:bg-surface-3 hover:text-ink hover:border-border-strong",
    primaire: "bg-accent border-accent text-accent-ink hover:brightness-110",
    danger: "bg-crit border-crit text-white hover:brightness-110",
  }[variante];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-[7px] whitespace-nowrap rounded-lg border px-[15px] py-2 text-[13px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function Chip({
  href,
  actif,
  children,
}: {
  href: string;
  actif: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-[13px] py-1.5 text-[12.5px] font-semibold transition-colors ${
        actif
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
      }`}
    >
      {children}
    </Link>
  );
}

export function ChipButton({
  actif,
  onClick,
  children,
}: {
  actif: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-[13px] py-1.5 text-[12.5px] font-semibold transition-colors ${
        actif
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

/* -------------------------------------------------------------------------
   Cartes
   ------------------------------------------------------------------------- */
export function Card({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`flex flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-card ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHead({
  titre,
  couleurPoint,
  action,
}: {
  titre: string;
  couleurPoint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-[9px] border-b border-border px-[18px] py-3.5">
      {couleurPoint && (
        <span className="size-[7px] shrink-0 rounded-full" style={{ background: couleurPoint }} />
      )}
      <h2 className="text-[13.5px] font-semibold">{titre}</h2>
      {action && <div className="ml-auto text-xs font-medium text-ink-faint">{action}</div>}
    </div>
  );
}

export function Empty({
  icone,
  children,
  action,
}: {
  icone: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-10 text-center text-[12.5px] leading-relaxed text-ink-faint">
      <span className="flex size-9 items-center justify-center rounded-full border border-border bg-surface-2 [&_svg]:size-[17px]">
        {icone}
      </span>
      <div>{children}</div>
      {action}
    </div>
  );
}

/* -------------------------------------------------------------------------
   Indicateurs
   ------------------------------------------------------------------------- */
export const TON_KPI: Record<string, { fond: string; texte: string; valeur: string }> = {
  crit: { fond: "bg-crit-soft", texte: "text-crit", valeur: "text-crit" },
  elev: { fond: "bg-elev-soft", texte: "text-elev", valeur: "text-elev" },
  moy: { fond: "bg-moy-soft", texte: "text-moy", valeur: "text-moy" },
  accent: { fond: "bg-accent-soft", texte: "text-accent", valeur: "text-ink" },
  gold: { fond: "bg-gold-soft", texte: "text-gold", valeur: "text-ink" },
  faib: { fond: "bg-faib-soft", texte: "text-faib", valeur: "text-faib" },
  violet: { fond: "bg-violet-soft", texte: "text-violet", valeur: "text-ink" },
  neutre: { fond: "bg-surface-3", texte: "text-ink-soft", valeur: "text-ink" },
};

export function Kpi({
  ton = "neutre",
  icone,
  label,
  valeur,
  detail,
  href,
  grand = false,
}: {
  ton?: keyof typeof TON_KPI;
  icone: React.ReactNode;
  label: string;
  valeur: number | string;
  detail?: string;
  /** Rend la tuile cliquable — navigue vers la vue filtree correspondante. */
  href?: string;
  /** Mise en avant visuelle (ex : "Actifs clean") — valeur plus grande. */
  grand?: boolean;
}) {
  const t = TON_KPI[ton];
  const Conteneur = href ? Link : "div";
  return (
    <Conteneur
      {...(href ? { href } : {})}
      className={`kpi-tuile rounded-2xl border border-border bg-surface px-[19px] py-[17px] shadow-card ${
        href ? "block transition-colors hover:border-border-strong hover:bg-surface-2" : ""
      }`}
    >
      <div className="flex items-center gap-[9px]">
        <span
          className={`flex size-[30px] items-center justify-center rounded-lg [&_svg]:size-[15px] ${t.fond} ${t.texte}`}
        >
          {icone}
        </span>
        <span className="text-[12.5px] font-medium text-ink-soft">{label}</span>
      </div>
      <div
        className={`tabular mt-3 font-mono leading-tight font-semibold ${grand ? "text-[40px]" : "text-[32px]"} ${t.valeur}`}
      >
        {valeur}
      </div>
      {detail && <div className="mt-[3px] text-[11.5px] text-ink-faint">{detail}</div>}
    </Conteneur>
  );
}

const TON_STAT: Record<string, string> = {
  neutre: "before:bg-border-strong",
  accent: "before:bg-accent",
  gold: "before:bg-gold [&_.v]:text-gold",
  crit: "before:bg-crit [&_.v]:text-crit",
  faib: "before:bg-faib [&_.v]:text-faib",
  violet: "before:bg-violet",
};

/** Stat compacte, pour les pages dotees d'une colonne laterale. */
export function Stat({
  ton = "neutre",
  valeur,
  label,
}: {
  ton?: keyof typeof TON_STAT;
  valeur: number | string;
  label: string;
}) {
  return (
    <div
      className={`relative min-w-[88px] overflow-hidden rounded-xl border border-border bg-surface px-4 py-[9px] shadow-card before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:content-[''] ${TON_STAT[ton]}`}
    >
      <div className="v tabular font-mono text-[19px] leading-tight font-semibold">{valeur}</div>
      <div className="mt-0.5 font-mono text-[9.5px] font-semibold tracking-[0.11em] whitespace-nowrap text-ink-faint uppercase">
        {label}
      </div>
    </div>
  );
}

export function Bar({
  label,
  valeur,
  total,
  couleur,
}: {
  label: string;
  valeur: number;
  total: number;
  couleur: string;
}) {
  const largeur = total > 0 ? Math.round((valeur / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-[12.5px]">
      <span className="w-[100px] shrink-0 text-ink-soft">{label}</span>
      <span className="h-[7px] flex-1 overflow-hidden rounded-full bg-surface-3">
        <span
          className="block h-full rounded-full transition-[width] duration-500"
          style={{ width: `${largeur}%`, background: couleur }}
        />
      </span>
      <span className="tabular w-[26px] text-right font-mono text-[12.5px] font-semibold">
        {valeur}
      </span>
    </div>
  );
}

/* -------------------------------------------------------------------------
   Modale
   ------------------------------------------------------------------------- */
export function Modal({
  ouvert,
  titre,
  onFermer,
  children,
}: {
  ouvert: boolean;
  titre: string;
  onFermer: () => void;
  children: React.ReactNode;
}) {
  // Portail vers document.body : sans lui, une modale ouverte depuis un
  // ancetre en position:sticky (ex : la colonne Actifs, dans sa barre
  // laterale collante) heritait du contexte d'empilement de cet ancetre —
  // elle se retrouvait visuellement DERRIERE le contenu principal (rendu
  // apres la sidebar, sans z-index concurrent) au lieu de flotter au-dessus
  // de toute la page. `position: fixed` echappe au flux et au clipping des
  // ancetres, mais PAS a leur contexte d'empilement s'ils en creent un.
  const [monte, setMonte] = useState(false);
  useEffect(() => setMonte(true), []);

  if (!ouvert || !monte) return null;
  return createPortal(
    <div
      className="fixed inset-0 z-[999] flex items-center justify-center overflow-y-auto bg-black/70 p-6 backdrop-blur-[3px]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onFermer();
      }}
    >
      <div className="relative w-full max-w-[480px] rounded-2xl border border-border-strong bg-surface px-[26px] py-6 shadow-pop">
        <button
          type="button"
          onClick={onFermer}
          aria-label="Fermer"
          className="absolute top-4 right-4 flex size-[30px] items-center justify-center rounded-lg text-ink-faint hover:bg-surface-2 hover:text-ink"
        >
          <IconClose />
        </button>
        <h2 className="mb-5 pr-8 font-display text-base font-bold tracking-tight">{titre}</h2>
        {children}
      </div>
    </div>,
    document.body
  );
}

/* -------------------------------------------------------------------------
   Formulaires
   ------------------------------------------------------------------------- */
export function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-1.5 block font-mono text-[10.5px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
      {children}
    </label>
  );
}

/** Interrupteur on/off — pour un reglage binaire (ex : Profil > afficher les
 * compteurs de nav toujours / jamais), plutot qu'un Select a deux options. */
export function Toggle({
  actif,
  onChange,
  label,
}: {
  actif: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={actif}
      onClick={() => onChange(!actif)}
      className="inline-flex items-center gap-2.5"
    >
      <span
        className={`relative h-[22px] w-9 shrink-0 rounded-full transition-colors ${
          actif ? "bg-accent" : "bg-surface-3"
        }`}
      >
        <span
          className={`absolute top-[3px] size-4 rounded-full bg-white shadow-card transition-[left] ${
            actif ? "left-[19px]" : "left-[3px]"
          }`}
        />
      </span>
      {label && <span className="text-[13px] font-medium text-ink">{label}</span>}
    </button>
  );
}

const CHAMP =
  "w-full rounded-lg border border-border bg-surface-2 px-[11px] py-2 text-[13px] text-ink transition-colors placeholder:text-ink-faint hover:border-border-strong focus:border-accent focus:outline-none focus:ring-3 focus:ring-accent-soft";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${CHAMP} ${props.className ?? ""}`} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${CHAMP} min-h-[88px] resize-y ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${CHAMP} cursor-pointer ${props.className ?? ""}`} />;
}

export function ErreurChamp({ children }: { children?: string }) {
  if (!children) return null;
  return <p className="mt-1.5 text-xs font-semibold text-crit">{children}</p>;
}

/* -------------------------------------------------------------------------
   Divers
   ------------------------------------------------------------------------- */
export function Chevron({ ouvert }: { ouvert: boolean }) {
  return (
    <span
      className={`flex transition-transform duration-150 ${ouvert ? "rotate-90 text-accent" : "text-ink-faint"}`}
    >
      <IconChevron className="size-3.5" />
    </span>
  );
}

export function CheckPastille() {
  return (
    <span className="flex size-6 items-center justify-center rounded-lg bg-faib text-white">
      <IconCheck className="size-[13px]" />
    </span>
  );
}

export function Spinner({ texte = "Chargement…" }: { texte?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 px-5 py-16 text-[13px] text-ink-faint">
      <span className="size-3.5 animate-spin rounded-full border-2 border-border border-t-accent" />
      {texte}
    </div>
  );
}
