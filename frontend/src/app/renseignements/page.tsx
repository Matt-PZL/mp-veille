"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { AppShell, PageHead, Side } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import {
  Card,
  ConfBar,
  Empty,
  Input,
  SevDot,
  Spinner,
  Stat,
  StatusPill,
  NatureTag,
} from "@/components/ui";
import { IconPlus, IconSearch, IconShield } from "@/components/icons";
import { api } from "@/lib/api";
import { depuis, pluriel, tronquer } from "@/lib/format";
import type { ActifDuFeed, FeedItem } from "@/lib/types";

const CRITICITES = [
  ["", "Toutes"],
  ["critique", "Critique"],
  ["elevee", "Élevée"],
  ["faible", "Faible"],
] as const;

const TRIS = [
  ["date", "Date"],
  ["criticite", "Criticité"],
  ["statut", "Traitement"],
] as const;

function ColonneActifs({
  actifs,
  actifSel,
  triActifs,
  lien,
}: {
  actifs: ActifDuFeed[];
  actifSel: number | null;
  triActifs: string;
  lien: (p: Record<string, string | number | null>) => string;
}) {
  const [recherche, setRecherche] = useState("");
  const filtres = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return q ? actifs.filter((a) => a.libelle.toLowerCase().includes(q)) : actifs;
  }, [actifs, recherche]);

  const technique = filtres.filter((a) => a.type === "technique");
  const normatif = filtres.filter((a) => a.type === "normatif");

  const ligne = (a: ActifDuFeed) => {
    const sel = actifSel === a.id;
    return (
      <Link
        key={a.id}
        href={lien({ actif: a.id })}
        className={`relative flex items-center gap-2.5 rounded-lg px-[11px] py-[9px] text-[13px] transition-colors ${
          sel
            ? "bg-accent-soft font-semibold text-ink before:absolute before:top-[7px] before:bottom-[7px] before:left-0 before:w-[3px] before:rounded-r-[3px] before:bg-accent before:content-['']"
            : "text-ink-soft hover:bg-surface-2 hover:text-ink"
        }`}
      >
        <span className="min-w-0 flex-1 truncate">
          {a.libelle}
          {a.version && <span className="ml-1.5 font-mono text-[11.5px] font-normal text-ink-faint">{a.version}</span>}
        </span>
        <span
          className={`shrink-0 rounded-full px-[7px] py-px font-mono text-[11px] ${
            sel ? "bg-accent text-accent-ink" : "bg-surface-3 text-ink-faint"
          }`}
        >
          {a.nb}
        </span>
      </Link>
    );
  };

  const groupe = (titre: string, couleur: string) => (
    <div className="flex items-center gap-2 px-[11px] pt-4 pb-[7px] font-mono text-[10px] font-semibold tracking-[0.13em] text-ink-faint uppercase after:h-px after:flex-1 after:bg-border after:content-['']">
      <span className="size-1.5 rounded-full" style={{ background: couleur }} />
      {titre}
    </div>
  );

  return (
    <Side
      titre="Actifs"
      action={
        <Link
          href="/actifs"
          className="inline-flex items-center gap-1.5 rounded-lg border border-accent bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink hover:brightness-110"
        >
          <IconPlus className="size-3" />
          Ajouter
        </Link>
      }
    >
      <div className="mb-2.5">
        <Input
          placeholder="Rechercher un actif…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          className="text-[12.5px]"
        />
      </div>

      <div className="mb-1.5 flex gap-1.5">
        {(["az", "nb", "critique"] as const).map((t) => (
          <Link
            key={t}
            href={lien({ tri_actifs: t })}
            className={`flex-1 rounded-full border px-1 py-[5px] text-center text-[11px] font-semibold ${
              triActifs === t
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-border bg-surface-2 text-ink-soft hover:text-ink"
            }`}
          >
            {t === "az" ? "A–Z" : t === "nb" ? "Nb." : "Critiques"}
          </Link>
        ))}
      </div>

      <Link
        href={lien({ actif: null })}
        className={`flex items-center gap-2.5 rounded-lg px-[11px] py-[9px] text-[13px] ${
          actifSel === null ? "bg-accent-soft font-semibold text-ink" : "text-ink-soft hover:bg-surface-2"
        }`}
      >
        <span className="flex-1 font-semibold">Tous les actifs</span>
        <span
          className={`shrink-0 rounded-full px-[7px] py-px font-mono text-[11px] ${
            actifSel === null ? "bg-accent text-accent-ink" : "bg-surface-3 text-ink-faint"
          }`}
        >
          {actifs.length}
        </span>
      </Link>

      {groupe("Technique", "var(--color-accent)")}
      {technique.length ? (
        technique.map(ligne)
      ) : (
        <span className="block px-[11px] py-[9px] text-xs text-ink-faint italic">
          Aucun actif technique
        </span>
      )}

      {groupe("Normatif", "var(--color-violet)")}
      {normatif.length ? (
        normatif.map(ligne)
      ) : (
        <span className="block px-[11px] py-[9px] text-xs text-ink-faint italic">
          Aucun référentiel
        </span>
      )}
    </Side>
  );
}

function Contenu() {
  const params = useSearchParams();
  const router = useRouter();

  const actifSel = params.get("actif") ? Number(params.get("actif")) : null;
  const criticite = params.get("criticite") ?? "";
  const tri = params.get("tri") ?? "date";
  const triActifs = params.get("tri_actifs") ?? "az";

  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [actifs, setActifs] = useState<ActifDuFeed[]>([]);

  useEffect(() => {
    setItems(null);
    api
      .feed({ actif: actifSel ?? undefined, criticite: criticite || undefined, tri })
      .then(setItems)
      .catch(() => setItems([]));
  }, [actifSel, criticite, tri]);

  useEffect(() => {
    api.actifsDuFeed(triActifs).then(setActifs).catch(() => setActifs([]));
  }, [triActifs]);

  /** Construit une URL en conservant les autres filtres. */
  const lien = (modifs: Record<string, string | number | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(modifs)) {
      if (v === null || v === "") p.delete(k);
      else p.set(k, String(v));
    }
    const s = p.toString();
    return `/renseignements${s ? `?${s}` : ""}`;
  };

  const nbATraiter = items?.filter((i) => !i.traitement || i.traitement.statut === "a_traiter").length ?? 0;
  const nbCritiques = items?.filter((i) => i.renseignement.criticite === "critique").length ?? 0;
  const nbNouveaux = items?.filter((i) => !i.renseignement.consulte).length ?? 0;

  const libelleActif = actifs.find((a) => a.id === actifSel)?.libelle;

  return (
    <AppShell
      side={
        <ColonneActifs actifs={actifs} actifSel={actifSel} triActifs={triActifs} lien={lien} />
      }
      compteurs={{ aTraiter: nbATraiter, actifs: actifs.length }}
    >
      <PageHead
        titre="Renseignements"
        sous={
          <>
            Filtré sur vos actifs déclarés. Le flux complet est dans{" "}
            <Link href="/actualites" className="text-accent">
              Actualités
            </Link>
            .
          </>
        }
        stats={
          <>
            <Stat valeur={items?.length ?? "—"} label="Total" />
            <Stat ton="gold" valeur={nbATraiter} label="À traiter" />
            <Stat ton="crit" valeur={nbCritiques} label="Critiques" />
            <Stat ton="accent" valeur={nbNouveaux} label="Nouveaux" />
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-[7px]">
        {TRIS.map(([v, label]) => (
          <Link
            key={v}
            href={lien({ tri: v })}
            className={`rounded-full border px-[13px] py-1.5 text-[12.5px] font-semibold ${
              tri === v
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-border bg-surface-2 text-ink-soft hover:text-ink"
            }`}
          >
            {label}
          </Link>
        ))}
        <span className="flex-1" />
        {CRITICITES.map(([v, label]) => (
          <Link
            key={v || "toutes"}
            href={lien({ criticite: v || null })}
            className={`rounded-full border px-[13px] py-1.5 text-[12.5px] font-semibold ${
              criticite === v
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-border bg-surface-2 text-ink-soft hover:text-ink"
            }`}
          >
            {label}
          </Link>
        ))}
      </div>

      {items === null ? (
        <Spinner />
      ) : (
        <>
          <div className="flex items-baseline gap-2.5">
            <span className="tabular font-mono text-[19px] font-semibold">{items.length}</span>
            <span className="text-[13px] text-ink-soft">{libelleActif ?? "Tous les actifs"}</span>
          </div>

          {items.length ? (
            <div className="flex flex-col gap-3">
              {items.map(({ renseignement: r, traitement: t, match }) => (
                <Link
                  key={r.id}
                  href={`/renseignements/${r.id}`}
                  className={`relative block overflow-hidden rounded-2xl border border-border bg-surface py-4 pr-[18px] pl-[21px] shadow-card transition-colors before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:content-[''] hover:border-border-strong ${
                    {
                      critique: "before:bg-crit",
                      elevee: "before:bg-elev",
                      moyenne: "before:bg-moy",
                      faible: "before:bg-faib",
                      "": "before:bg-ink-faint",
                    }[r.criticite]
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <SevDot criticite={r.criticite} />
                    <span className="min-w-0 flex-1 text-[14.5px] leading-snug font-semibold tracking-tight">
                      {r.reference || r.source} — {r.titre}
                    </span>
                    {!r.consulte && (
                      <span className="shrink-0 rounded-[5px] bg-accent px-[7px] py-0.5 font-mono text-[9.5px] font-semibold tracking-[0.09em] text-accent-ink uppercase">
                        Nouveau
                      </span>
                    )}
                    <span className="shrink-0 font-mono text-[11.5px] text-ink-faint">
                      {depuis(r.decouvert_le)}
                    </span>
                  </div>

                  <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
                    {tronquer(r.description, 210)}
                  </p>

                  <div className="mt-2.5 flex flex-wrap items-center gap-2.5">
                    <span className="font-mono text-[11.5px] font-medium text-accent">{r.source}</span>
                    <NatureTag nature={r.nature} label={r.nature_label} />
                    {r.cvss_score !== null && (
                      <span className="font-mono text-[11.5px] text-ink-faint">
                        CVSS {r.cvss_score.toFixed(1)}
                      </span>
                    )}
                    {t ? (
                      <StatusPill statut={t.statut} label={t.statut_label} />
                    ) : (
                      <StatusPill statut="a_traiter" label="+ Traitement" />
                    )}
                    {match && <ConfBar palier={match.palier} pourcent={match.pourcent} />}
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <Card>
              <Empty
                icone={<IconShield />}
                action={
                  !actifs.length ? (
                    <Link
                      href="/actifs"
                      className="inline-flex items-center gap-[7px] rounded-lg border border-accent bg-accent px-[15px] py-2 text-[13px] font-semibold text-accent-ink"
                    >
                      <IconPlus className="size-3.5" />
                      Déclarer mon premier actif
                    </Link>
                  ) : undefined
                }
              >
                {actifSel ? (
                  <>
                    Aucun renseignement ne concerne <b>{libelleActif}</b> pour le moment.
                  </>
                ) : actifs.length ? (
                  <>
                    Aucun renseignement ne concerne vos actifs déclarés.
                    <br />
                    Le flux brut reste consultable dans{" "}
                    <Link href="/actualites" className="text-accent">
                      Actualités
                    </Link>
                    .
                  </>
                ) : (
                  <>
                    Déclarez d&apos;abord un actif : la veille ne peut rien vous remonter sans
                    savoir ce que vous exploitez.
                  </>
                )}
              </Empty>
            </Card>
          )}
        </>
      )}
    </AppShell>
  );
}

export default function PageRenseignements() {
  return (
    <Garde>
      <Suspense fallback={<Spinner />}>
        <Contenu />
      </Suspense>
    </Garde>
  );
}
