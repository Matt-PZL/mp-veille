"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell, PageHead } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import { Button, Card, Empty, Input, NatureTag, Spinner } from "@/components/ui";
import { IconNews, IconShield } from "@/components/icons";
import { api } from "@/lib/api";
import { depuis, pluriel, tronquer } from "@/lib/format";
import type { Renseignement } from "@/lib/types";

const TEXTE_SEV: Record<string, string> = {
  critique: "text-crit",
  elevee: "text-elev",
  moyenne: "text-moy",
  faible: "text-faib",
};

const BORD_SEV: Record<string, string> = {
  critique: "before:bg-crit",
  elevee: "before:bg-elev",
  moyenne: "before:bg-moy",
  faible: "before:bg-faib",
  "": "before:bg-ink-faint",
};

function Contenu() {
  const [items, setItems] = useState<Renseignement[] | null>(null);
  const [type, setType] = useState("");
  const [saisie, setSaisie] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    setItems(null);
    api
      .actualites({ q: q || undefined, type: type || undefined })
      .then(setItems)
      .catch(() => setItems([]));
  }, [q, type]);

  return (
    <AppShell>
      <PageHead
        titre="Actualités"
        sous={
          <>
            Flux complet de la base de connaissance — <b className="text-ink">non filtré</b> sur vos
            actifs déclarés.
          </>
        }
        actions={
          <Link
            href="/renseignements"
            className="inline-flex items-center gap-[7px] rounded-lg border border-border bg-surface-2 px-[15px] py-2 text-[13px] font-semibold text-ink-soft transition-colors hover:bg-surface-3 hover:text-ink"
          >
            <IconShield className="size-3.5" />
            Ce qui me concerne
          </Link>
        }
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQ(saisie);
        }}
        className="flex flex-wrap items-center gap-2"
      >
        {(
          [
            ["", "Tous"],
            ["technique", "Technique"],
            ["normatif", "Normatif"],
          ] as const
        ).map(([v, label]) => (
          <button
            key={v || "tous"}
            type="button"
            onClick={() => setType(v)}
            className={`rounded-full border px-[13px] py-1.5 text-[12.5px] font-semibold ${
              type === v
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-border bg-surface-2 text-ink-soft hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
        <Input
          placeholder="Rechercher un titre, une source…"
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          className="max-w-[360px] min-w-[200px] flex-1"
        />
        <Button type="submit" variante="primaire">
          Rechercher
        </Button>
        <span className="ml-auto font-mono text-xs text-ink-faint">
          {items?.length ?? 0} résultat{pluriel(items?.length ?? 0)}
        </span>
      </form>

      {items === null ? (
        <Spinner />
      ) : items.length ? (
        <div className="flex flex-col gap-3">
          {items.map((r) => (
            <article
              key={r.id}
              className={`relative overflow-hidden rounded-2xl border border-border bg-surface px-[22px] py-[17px] shadow-card transition-colors before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:content-[''] hover:border-border-strong hover:bg-surface-2 ${BORD_SEV[r.criticite]}`}
            >
              <div className="mb-2.5 flex flex-wrap items-center gap-2.5 text-[11.5px]">
                {r.url_source ? (
                  <a
                    href={r.url_source}
                    target="_blank"
                    rel="noopener"
                    className="font-mono font-medium text-accent hover:underline"
                  >
                    {r.source} ↗
                  </a>
                ) : (
                  <span className="font-mono font-medium text-accent">{r.source}</span>
                )}
                {r.reference && <span className="font-mono text-ink-faint">{r.reference}</span>}
                <NatureTag nature={r.nature} label={r.nature_label} />
                {r.criticite_label && (
                  <span
                    className={`text-[10px] font-bold tracking-[0.06em] uppercase ${TEXTE_SEV[r.criticite] ?? "text-ink-faint"}`}
                  >
                    {r.criticite_label}
                  </span>
                )}
                {r.cvss_score !== null && (
                  <span className="font-mono text-ink-faint">CVSS {r.cvss_score.toFixed(1)}</span>
                )}
                <span className="ml-auto font-mono text-ink-faint">{depuis(r.decouvert_le)}</span>
              </div>
              <h3 className="mb-[7px] text-[15px] leading-snug font-semibold tracking-tight text-balance">
                {r.titre}
              </h3>
              <p className="text-[13px] leading-relaxed text-ink-soft">
                {tronquer(r.description, 260)}
              </p>
              <div className="mt-3.5 flex flex-wrap gap-1.5">
                {[r.type_label, r.taxonomie_editeur, r.taxonomie_produit, r.taxonomie_referentiel]
                  .filter(Boolean)
                  .map((tag, i) => (
                    <span
                      key={i}
                      className="rounded-md bg-surface-3 px-2.5 py-[2.5px] font-mono text-[10.5px] font-medium text-ink-faint"
                    >
                      {tag}
                    </span>
                  ))}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Card>
          <Empty icone={<IconNews />}>
            {q ? `Aucune actualité pour « ${q} ».` : "La base est vide — aucune collecte n'a encore tourné."}
          </Empty>
        </Card>
      )}
    </AppShell>
  );
}

export default function PageActualites() {
  return (
    <Garde>
      <Contenu />
    </Garde>
  );
}
