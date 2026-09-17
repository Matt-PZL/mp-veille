"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AppShell, PageHead, Side } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import {
  Bar,
  Card,
  CardHead,
  Empty,
  Input,
  NatureTag,
  SevDot,
  Spinner,
  Stat,
  StatusPill,
} from "@/components/ui";
import { IconCheck, IconDownload, IconSearch } from "@/components/icons";
import { api } from "@/lib/api";
import { dateCourte, depuis, tronquer } from "@/lib/format";
import type { CompteursTraitement, TraitementItem } from "@/lib/types";

const STATUTS = [
  ["a_traiter", "À traiter", "bg-gold shadow-[0_0_0_3px_var(--color-gold-soft)]"],
  ["en_cours", "Démarré", "bg-statut-demarre shadow-[0_0_0_3px_var(--color-statut-demarre-soft)]"],
  ["clos", "Clos", "bg-faib shadow-[0_0_0_3px_var(--color-faib-soft)]"],
  ["non_applicable", "Non applicable", "bg-ink-faint"],
] as const;

function Contenu() {
  const params = useSearchParams();
  const statut = params.get("statut") ?? "";
  const tri = params.get("tri") ?? "recent";
  const criticite = params.get("criticite") ?? "";

  const [items, setItems] = useState<TraitementItem[] | null>(null);
  const [compteurs, setCompteurs] = useState<CompteursTraitement>({});
  const [recherche, setRecherche] = useState(params.get("q") ?? "");
  const [q, setQ] = useState(params.get("q") ?? "");
  const [ouvert, setOuvert] = useState<number | null>(null);

  useEffect(() => {
    setItems(null);
    api
      .traitements({ statut: statut || undefined, tri, criticite: criticite || undefined, q: q || undefined })
      .then(setItems)
      .catch(() => setItems([]));
  }, [statut, tri, criticite, q]);

  useEffect(() => {
    api.compteursTraitement().then(setCompteurs).catch(() => {});
  }, [items]);

  const lien = (modifs: Record<string, string | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(modifs)) {
      if (v === null || v === "") p.delete(k);
      else p.set(k, v);
    }
    const s = p.toString();
    return `/app/traitement${s ? `?${s}` : ""}`;
  };

  const total = compteurs.total ?? 0;

  const ligneStatut = (code: string, label: string, pastille: string, n: number) => {
    const sel = statut === code;
    return (
      <Link
        key={code}
        href={lien({ statut: code })}
        className={`relative flex items-center gap-2.5 rounded-lg px-[11px] py-[9px] text-[13px] transition-colors ${
          sel
            ? "bg-accent-soft font-semibold text-ink before:absolute before:top-[7px] before:bottom-[7px] before:left-0 before:w-[3px] before:rounded-r-[3px] before:bg-accent before:content-['']"
            : "text-ink-soft hover:bg-surface-2 hover:text-ink"
        }`}
      >
        <span className="flex min-w-0 flex-1 items-center gap-2.5">
          <span className={`size-2 shrink-0 rounded-full ${pastille}`} />
          {label}
        </span>
        <span
          className={`shrink-0 rounded-full px-[7px] py-px font-mono text-[11px] ${
            sel ? "bg-accent text-accent-ink" : "bg-surface-3 text-ink-faint"
          }`}
        >
          {n}
        </span>
      </Link>
    );
  };

  return (
    <AppShell
      side={
        <Side titre="Statuts">
          <Link
            href={lien({ statut: null })}
            className={`flex items-center gap-2.5 rounded-lg px-[11px] py-[9px] text-[13px] ${
              !statut ? "bg-accent-soft font-semibold text-ink" : "text-ink-soft hover:bg-surface-2"
            }`}
          >
            <span className="flex-1">Tous</span>
            <span
              className={`shrink-0 rounded-full px-[7px] py-px font-mono text-[11px] ${
                !statut ? "bg-accent text-accent-ink" : "bg-surface-3 text-ink-faint"
              }`}
            >
              {total}
            </span>
          </Link>
          {STATUTS.map(([code, label, pastille]) =>
            ligneStatut(code, label, pastille, compteurs[code] ?? 0)
          )}
          <div className="my-2.5 h-px bg-border" />
          <Link
            href={lien({ statut: "en_retard" })}
            className={`flex items-center gap-2.5 rounded-lg px-[11px] py-[9px] text-[13px] ${
              statut === "en_retard"
                ? "bg-accent-soft font-semibold"
                : "text-ink-soft hover:bg-surface-2"
            }`}
          >
            <span className="flex-1 text-crit">En retard</span>
            <span className="shrink-0 rounded-full bg-surface-3 px-[7px] py-px font-mono text-[11px] text-ink-faint">
              {compteurs.en_retard ?? 0}
            </span>
          </Link>
        </Side>
      }
    >
      <PageHead
        titre="Traitement"
        sous="Chaque décision horodatée et justifiée constitue votre preuve d'audit."
        stats={
          <>
            <Stat ton="gold" valeur={compteurs.a_traiter ?? 0} label="À traiter" />
            <Stat ton="accent" valeur={compteurs.en_cours ?? 0} label="Démarré" />
            <Stat ton="faib" valeur={compteurs.clos ?? 0} label="Clos" />
            <Stat ton="crit" valeur={compteurs.en_retard ?? 0} label="En retard" />
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQ(recherche);
          }}
          className="flex min-w-[220px] flex-1 items-center gap-2 sm:max-w-[320px]"
        >
          <Input
            placeholder="Rechercher un actif, une référence…"
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            className="text-[12.5px]"
          />
        </form>
        <span className="flex-1" />
        {(
          [
            ["recent", "Récent"],
            ["criticite", "Criticité"],
            ["echeance", "Échéance"],
          ] as const
        ).map(([v, label]) => (
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
      </div>

      <Card>
        <div className="grid grid-cols-[20px_150px_1fr_120px_92px_86px_40px] items-center gap-3 border-b border-border bg-surface-2 px-[18px] py-[11px] font-mono text-[10px] font-semibold tracking-[0.1em] text-ink-faint uppercase max-xl:grid-cols-[20px_130px_1fr_110px_40px]">
          <span />
          <span>Actif</span>
          <span>Renseignement</span>
          <span>Statut</span>
          <span className="max-xl:hidden">Échéance</span>
          <span className="max-xl:hidden">Maj</span>
          <span />
        </div>

        {items === null ? (
          <Spinner />
        ) : items.length ? (
          items.map(({ traitement: t, renseignement: r }) => (
            <div key={t.id} className="border-b border-border last:border-b-0">
              <div
                role="button"
                tabIndex={0}
                onClick={() => setOuvert(ouvert === t.id ? null : t.id)}
                onKeyDown={(e) => e.key === "Enter" && setOuvert(ouvert === t.id ? null : t.id)}
                className="grid cursor-pointer grid-cols-[20px_150px_1fr_120px_92px_86px_40px] items-center gap-3 px-[18px] py-3 text-[13px] hover:bg-surface-2 max-xl:grid-cols-[20px_130px_1fr_110px_40px]"
              >
                <SevDot criticite={r?.criticite ?? ""} />
                <span className="truncate text-[12.5px] text-ink-soft">
                  {t.actif?.libelle ?? "—"}
                </span>
                <span className="truncate font-medium">
                  {r ? `${r.reference || r.source} — ${r.titre}` : "Renseignement retiré de la BDP"}
                </span>
                <StatusPill statut={t.statut} label={t.statut_label} />
                <span
                  className={`font-mono text-[11.5px] max-xl:hidden ${t.en_retard ? "font-semibold text-crit" : "text-ink-faint"}`}
                >
                  {t.echeance ? dateCourte(t.echeance) : "—"}
                </span>
                <span className="font-mono text-[11.5px] text-ink-faint max-xl:hidden">
                  {depuis(t.maj_le)}
                </span>
                <a
                  href={api.urlPdf(t.id)}
                  target="_blank"
                  rel="noopener"
                  onClick={(e) => e.stopPropagation()}
                  title="Exporter en PDF"
                  className="flex items-center justify-center rounded-md p-1 text-ink-faint hover:bg-surface-3 hover:text-ink"
                >
                  <IconDownload className="size-[15px]" />
                </a>
              </div>

              {ouvert === t.id && (
                <div className="border-t border-border bg-surface-2 px-[18px] py-4 pl-[52px]">
                  {r ? (
                    <>
                      <div className="mb-2.5 flex flex-wrap items-center gap-2.5">
                        {r.url_source ? (
                          <a
                            href={r.url_source}
                            target="_blank"
                            rel="noopener"
                            className="font-mono text-[11.5px] font-medium text-accent"
                          >
                            {r.source} ↗
                          </a>
                        ) : (
                          <span className="font-mono text-[11.5px] text-ink-faint">{r.source}</span>
                        )}
                        <NatureTag nature={r.nature} label={r.nature_label} />
                        {r.cvss_score !== null && (
                          <span className="font-mono text-[11.5px] text-ink-faint">
                            CVSS {r.cvss_score.toFixed(1)}
                          </span>
                        )}
                      </div>
                      <p className="mb-3.5 max-w-[76ch] text-[12.5px] leading-relaxed text-ink-soft">
                        {tronquer(r.description, 420)}
                      </p>
                      {t.justificatif && (
                        <p className="mb-3.5 max-w-[76ch] text-[12.5px] leading-relaxed text-ink-soft">
                          <b className="text-ink">Justificatif —</b> {t.justificatif}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="mb-3.5 text-[12.5px] text-ink-soft">
                      Ce renseignement a été retiré de la BDP depuis ce traitement.
                    </p>
                  )}
                  <Link
                    href={`/app/renseignements/${t.id_renseignement}`}
                    className="inline-flex items-center gap-[7px] rounded-lg border border-accent bg-accent px-[15px] py-2 text-[13px] font-semibold text-accent-ink"
                  >
                    Ouvrir le traitement
                  </Link>
                </div>
              )}
            </div>
          ))
        ) : (
          <Empty icone={<IconSearch />}>
            {total ? (
              "Aucun traitement ne correspond à ces critères."
            ) : (
              <>
                Aucun renseignement n&apos;a encore été pris en charge.
                <br />
                Ouvrez-en un depuis{" "}
                <Link href="/app/renseignements" className="text-accent">
                  Renseignements
                </Link>{" "}
                pour poser un premier statut.
              </>
            )}
          </Empty>
        )}
      </Card>

      <div className="grid gap-3.5 lg:grid-cols-2">
        <Card>
          <CardHead titre="Répartition par statut" couleurPoint="var(--color-accent)" />
          <div className="flex flex-col gap-3 px-[18px] py-4">
            <Bar label="À traiter" valeur={compteurs.a_traiter ?? 0} total={total} couleur="var(--color-gold)" />
            <Bar label="Démarré" valeur={compteurs.en_cours ?? 0} total={total} couleur="var(--color-accent)" />
            <Bar label="Clos" valeur={compteurs.clos ?? 0} total={total} couleur="var(--color-faib)" />
            <Bar
              label="Non applicable"
              valeur={compteurs.non_applicable ?? 0}
              total={total}
              couleur="var(--color-ink-faint)"
            />
          </div>
        </Card>

        <Card>
          <CardHead titre="En retard" couleurPoint="var(--color-crit)" />
          <div className="flex flex-1 flex-col">
            {items?.filter((i) => i.traitement.en_retard).length ? (
              items
                .filter((i) => i.traitement.en_retard)
                .slice(0, 6)
                .map(({ traitement: t, renseignement: r }) => (
                  <Link
                    key={t.id}
                    href={`/app/renseignements/${t.id_renseignement}`}
                    className="flex items-baseline gap-2.5 border-b border-border px-4 py-[11px] text-[12.5px] text-ink-soft last:border-b-0 hover:bg-surface-2 hover:text-ink"
                  >
                    <span className="shrink-0 font-mono text-[11px] font-semibold text-crit">
                      {dateCourte(t.echeance)}
                    </span>
                    <span className="truncate">
                      {t.actif?.libelle ?? "—"} — {tronquer(r?.titre ?? "", 34)}
                    </span>
                  </Link>
                ))
            ) : (
              <Empty icone={<IconCheck />}>Aucun retard.</Empty>
            )}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

export default function PageTraitement() {
  return (
    <Garde>
      <Suspense fallback={<Spinner />}>
        <Contenu />
      </Suspense>
    </Garde>
  );
}
