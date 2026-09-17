"use client";

/**
 * Coque de l'application, en deux dispositions au choix de l'utilisateur
 * (reglable dans Profil → Apparence) :
 *
 *   horizontale — tout sur une seule ligne : marque, onglets, recherche et
 *                 preferences.
 *
 *   verticale   — comme au debut du projet : un bouton a gauche de la barre
 *                 ouvre un tiroir lateral superpose au contenu, avec un
 *                 voile derriere. Le tiroir n'occupe aucune largeur tant
 *                 qu'il est ferme, contrairement a un rail permanent.
 *
 * Les deux partagent le meme emplacement lateral `side` (actifs, statuts) et
 * la meme zone de contenu : une page n'a pas a savoir quelle nav est active.
 */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useUi } from "@/lib/ui-context";
import { depuis } from "@/lib/format";
import { api } from "@/lib/api";
import type { CompteursNav } from "@/lib/types";
import {
  IconBars,
  IconClipboard,
  IconClose,
  IconDashboard,
  IconLogout,
  IconMoon,
  IconNews,
  IconPalette,
  IconSearch,
  IconServer,
  IconShield,
  IconSun,
  IconUser,
} from "./icons";

const ONGLETS = [
  { href: "/app", label: "Vue d'ensemble", Icone: IconDashboard, cle: null, separeAvant: false },
  { href: "/app/renseignements", label: "Renseignements", Icone: IconShield, cle: "aTraiter", separeAvant: false },
  { href: "/app/actifs", label: "Actifs", Icone: IconServer, cle: "actifs", separeAvant: false },
  { href: "/app/traitement", label: "Traitement", Icone: IconClipboard, cle: "traitements", separeAvant: true },
  { href: "/app/actualites", label: "Actualités", Icone: IconNews, cle: null, separeAvant: false },
] as const;

/* ------------------------------------------------------------------ */
/* Elements communs aux deux dispositions                              */
/* ------------------------------------------------------------------ */

function Marque() {
  return (
    <Link href="/app" className="flex shrink-0 items-center gap-2.5">
      <span className="flex size-7 items-center justify-center rounded-[9px] bg-accent font-display text-sm font-extrabold text-accent-ink">
        V
      </span>
      <span className="font-display text-base font-bold tracking-tight max-sm:hidden">veille</span>
    </Link>
  );
}

function Recherche({ className = "" }: { className?: string }) {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={() => router.push("/app/actualites")}
      className={`flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-[11px] py-[7px] text-[13px] text-ink-faint transition-colors hover:border-border-strong ${className}`}
    >
      <IconSearch className="size-[15px]" />
      <span className="flex-1 text-left max-xl:hidden">Rechercher un actif, une CVE…</span>
      <kbd className="rounded border border-border bg-bg px-1.5 py-px font-mono text-[10.5px] max-xl:hidden">
        /
      </kbd>
    </button>
  );
}

function Preferences({
  menu,
  setMenu,
}: {
  menu: string | null;
  setMenu: (m: string | null) => void;
}) {
  const router = useRouter();
  const { utilisateur, deconnexion } = useAuth();
  const { mode, accent, basculerMode, choisirAccent } = useUi();

  return (
    <>
      <button
        type="button"
        onClick={basculerMode}
        title="Basculer clair / sombre"
        className="flex size-[34px] shrink-0 items-center justify-center rounded-lg border border-transparent text-ink-soft transition-colors hover:border-border hover:bg-surface-2 hover:text-ink"
      >
        {mode === "dark" ? <IconSun /> : <IconMoon />}
      </button>

      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setMenu(menu === "accent" ? null : "accent")}
          title="Couleur d'accent"
          className="flex size-[34px] items-center justify-center rounded-lg border border-transparent text-ink-soft transition-colors hover:border-border hover:bg-surface-2 hover:text-ink"
        >
          <IconPalette />
        </button>
        {menu === "accent" && (
          <div className="absolute top-[calc(100%+6px)] right-0 z-50 min-w-[200px] rounded-xl border border-border bg-surface p-1.5 shadow-pop">
            {(
              [
                ["bleu", "#3B7BFF", "Bleu"],
                ["vert", "#3DBB6E", "Vert"],
                ["violet", "#A371F7", "Violet"],
              ] as const
            ).map(([cle, couleur, label]) => (
              <button
                key={cle}
                type="button"
                onClick={() => {
                  choisirAccent(cle);
                  setMenu(null);
                }}
                className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-surface-2 hover:text-ink ${
                  accent === cle ? "bg-surface-2 text-ink" : "text-ink-soft"
                }`}
              >
                <span className="size-2.5 rounded-full" style={{ background: couleur }} />
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setMenu(menu === "compte" ? null : "compte")}
          className="flex items-center gap-2.5 rounded-full border border-border bg-surface-2 py-1 pr-2.5 pl-1 transition-colors hover:border-border-strong"
        >
          <span className="flex size-[26px] items-center justify-center rounded-full bg-accent-soft font-mono text-[10.5px] font-bold text-accent uppercase">
            {utilisateur?.username.slice(0, 2)}
          </span>
          <span className="max-w-[110px] truncate text-[12.5px] font-semibold max-lg:hidden">
            {utilisateur?.username}
          </span>
        </button>
        {menu === "compte" && (
          <div className="absolute top-[calc(100%+6px)] right-0 z-50 min-w-[200px] rounded-xl border border-border bg-surface p-1.5 shadow-pop">
            <div className="mb-1 border-b border-border px-2.5 pt-2 pb-2.5 text-xs text-ink-faint">
              {utilisateur?.email || utilisateur?.username}
            </div>
            <Link
              href="/app/profil"
              onClick={() => setMenu(null)}
              className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <IconUser className="size-4" />
              Profil et apparence
            </Link>
            <div className="my-1.5 h-px bg-border" />
            <button
              type="button"
              onClick={async () => {
                setMenu(null);
                await deconnexion();
                router.push("/connexion");
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <IconLogout className="size-4" />
              Se déconnecter
            </button>
          </div>
        )}
      </div>
    </>
  );
}

function EtatCollecte({ derniereCollecte }: { derniereCollecte: string | null | undefined }) {
  if (derniereCollecte === undefined) return null;
  return (
    <span className="flex shrink-0 items-center gap-2 font-mono text-[11px] text-ink-faint">
      <span
        className={`size-[7px] shrink-0 rounded-full ${
          derniereCollecte
            ? "bg-faib shadow-[0_0_0_3px_var(--color-faib-soft)]"
            : "bg-ink-faint shadow-[0_0_0_3px_var(--color-surface-3)]"
        }`}
      />
      {derniereCollecte ? (
        <>
          Collecte <b className="font-medium text-ink-soft">il y a {depuis(derniereCollecte)}</b>
        </>
      ) : (
        <b className="font-medium text-ink-soft">Aucune collecte</b>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ */

export function AppShell({
  side,
  derniereCollecte,
  children,
}: {
  side?: React.ReactNode;
  derniereCollecte?: string | null;
  children: React.ReactNode;
}) {
  const chemin = usePathname();
  const [menu, setMenu] = useState<string | null>(null);
  const [tiroir, setTiroir] = useState(false);
  const zone = useRef<HTMLElement>(null);

  // Source unique des pastilles de nav : recuperee une fois ici, plutot que
  // chaque page ne fournisse (ou pas) son propre sous-ensemble de compteurs —
  // c'est ce qui faisait apparaitre/disparaitre les badges selon la page
  // ouverte, pas selon une vraie absence de donnee.
  const [compteursNav, setCompteursNav] = useState<CompteursNav | null>(null);
  const [afficherCompteurs, setAfficherCompteurs] = useState(true);

  useEffect(() => {
    api.compteursNav().then(setCompteursNav).catch(() => {});
    api
      .preferences()
      .then((p) => setAfficherCompteurs(p.afficher_compteurs_nav))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!menu) return;
    const fermer = (e: MouseEvent) => {
      if (!zone.current?.contains(e.target as Node)) setMenu(null);
    };
    document.addEventListener("pointerdown", fermer);
    return () => document.removeEventListener("pointerdown", fermer);
  }, [menu]);

  // Echap ferme ce qui est ouvert, tiroir en premier.
  useEffect(() => {
    const echap = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (tiroir) setTiroir(false);
      else setMenu(null);
    };
    document.addEventListener("keydown", echap);
    return () => document.removeEventListener("keydown", echap);
  }, [tiroir]);

  // Le tiroir se referme des qu'on change de page : sinon il resterait
  // ouvert par-dessus la page qu'on vient d'ouvrir.
  useEffect(() => setTiroir(false), [chemin]);

  const estActif = (href: string) => (href === "/app" ? chemin === "/app" : chemin.startsWith(href));
  const CLE_VERS_COMPTEUR: Record<string, keyof CompteursNav> = {
    aTraiter: "a_traiter",
    traitements: "traitements",
    actifs: "actifs",
  };
  const compteur = (cle: string | null) =>
    cle && compteursNav ? compteursNav[CLE_VERS_COMPTEUR[cle]] : undefined;

  const pastille = (n: number, actif: boolean) => (
    <span
      className={`rounded-full px-1.5 py-px font-mono text-[10.5px] font-medium ${
        actif ? "bg-accent text-accent-ink" : "bg-surface-3 text-ink-faint"
      }`}
    >
      {n}
    </span>
  );

  return (
    <div className="flex min-h-screen flex-col">
      {/* ---------------- Barre superieure ----------------
          Rangee 1 : commune aux deux dispositions.
          Rangee 2 : les onglets, uniquement en horizontal — masquee par le
          CSS en vertical, ou la navigation vit dans le tiroir. */}
      <header
        ref={zone}
        className="sticky top-0 z-40 flex shrink-0 flex-col border-b border-border bg-surface"
      >
        <div className="flex h-14 items-center gap-3 px-[18px] lg:px-8">
          <button
            type="button"
            data-quand-nav="verticale"
            onClick={() => setTiroir(true)}
            aria-label="Ouvrir la navigation"
            aria-expanded={tiroir}
            className="flex size-[34px] shrink-0 items-center justify-center rounded-lg border border-transparent text-ink-soft transition-colors hover:border-border hover:bg-surface-2 hover:text-ink"
          >
            <IconBars />
          </button>

          <Marque />

          <Recherche className="ml-auto w-[340px] shrink-0 max-lg:w-auto" />
          <Preferences menu={menu} setMenu={setMenu} />
        </div>

        <nav
          data-quand-nav="horizontale"
          className="flex h-12 items-center gap-1.5 overflow-x-auto border-t border-border px-[18px] [scrollbar-width:none] lg:px-8 [&::-webkit-scrollbar]:hidden"
        >
          {ONGLETS.map(({ href, label, Icone, cle, separeAvant }) => {
            const n = compteur(cle);
            const actif = estActif(href);
            return (
              <span key={href} className="flex shrink-0 items-center">
                {separeAvant && <span className="mx-1.5 h-5 w-px shrink-0 bg-border" />}
                <Link
                  href={href}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-full px-3.5 py-[7px] text-[13.5px] font-semibold whitespace-nowrap transition-colors ${
                    actif
                      ? "bg-accent-soft text-ink [&_svg]:text-accent"
                      : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                  }`}
                >
                  <Icone className="size-4" />
                  {label}
                  {afficherCompteurs && n !== undefined && pastille(n, actif)}
                </Link>
              </span>
            );
          })}

          {derniereCollecte !== undefined && (
            <span className="ml-auto shrink-0 pl-4 max-lg:hidden">
              <EtatCollecte derniereCollecte={derniereCollecte} />
            </span>
          )}
        </nav>
      </header>

      {/* ---------------- Tiroir lateral (disposition verticale) ---------------- */}
      <div data-quand-nav="verticale">
          <div
            onClick={() => setTiroir(false)}
            className={`fixed inset-0 z-49 bg-black/70 backdrop-blur-[2px] transition-opacity duration-150 ${
              tiroir ? "opacity-100" : "pointer-events-none opacity-0"
            }`}
          />
          <nav
            aria-hidden={!tiroir}
            className={`fixed inset-y-0 left-0 z-50 flex w-[284px] flex-col border-r border-border bg-surface px-3 py-4 shadow-pop transition-transform duration-200 ${
              tiroir ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <div className="flex items-center justify-between px-1.5 pb-3.5">
              <Marque />
              <button
                type="button"
                onClick={() => setTiroir(false)}
                aria-label="Fermer la navigation"
                className="flex size-[30px] items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
              >
                <IconClose />
              </button>
            </div>

            <div className="flex flex-col gap-0.5">
              {ONGLETS.map(({ href, label, Icone, cle, separeAvant }) => {
                const n = compteur(cle);
                const actif = estActif(href);
                return (
                  <span key={href}>
                    {separeAvant && <span className="my-2 block h-px bg-border" />}
                    <Link
                      href={href}
                      tabIndex={tiroir ? 0 : -1}
                      className={`relative flex items-center gap-3 rounded-lg px-2.5 py-[9px] text-[13.5px] font-medium transition-colors ${
                        actif
                          ? "bg-accent-soft font-semibold text-ink [&_svg]:text-accent"
                          : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                      }`}
                    >
                      <Icone className="size-[17px] shrink-0" />
                      <span className="flex-1 truncate">{label}</span>
                      {afficherCompteurs && n !== undefined && pastille(n, actif)}
                    </Link>
                  </span>
                );
              })}
            </div>

            {derniereCollecte !== undefined && (
              <div className="mt-auto rounded-xl border border-border bg-surface-2 px-3 py-3">
                <EtatCollecte derniereCollecte={derniereCollecte} />
              </div>
            )}
          </nav>
      </div>

      {/* ---------------- Corps : colonne laterale de page + contenu ---------------- */}
      <div className="flex min-h-0 flex-1 items-stretch max-lg:flex-col">
        {side}
        <div className="flex min-w-0 flex-1 flex-col gap-5 px-[18px] pt-7 pb-20 lg:px-8">
          {children}
        </div>
      </div>
    </div>
  );
}

/** Colonne laterale pleine hauteur, collante sous la barre de navigation. */
export function Side({
  titre,
  action,
  children,
}: {
  titre: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <aside className="w-[272px] shrink-0 overflow-y-auto border-r border-border bg-surface px-3.5 pt-5 pb-8 max-lg:w-auto max-lg:border-r-0 max-lg:border-b lg:sticky lg:top-[var(--h-top,56px)] lg:h-[calc(100vh-var(--h-top,56px))]">
      <div className="mb-3.5 flex items-center justify-between gap-2.5">
        <h2 className="font-display text-[15px] font-bold tracking-tight">{titre}</h2>
        {action}
      </div>
      {children}
    </aside>
  );
}

export function PageHead({
  titre,
  sous,
  actions,
  stats,
}: {
  titre: string;
  sous?: React.ReactNode;
  actions?: React.ReactNode;
  stats?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-5">
      <div>
        <h1 className="font-display text-[26px] leading-tight font-extrabold tracking-tight">
          {titre}
        </h1>
        {sous && <p className="mt-1 text-[13.5px] text-ink-soft">{sous}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      {stats && <div className="flex flex-wrap gap-2.5">{stats}</div>}
    </div>
  );
}
