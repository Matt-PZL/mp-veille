"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
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
import {
  IconChevron,
  IconClipboard,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconServer,
  IconShield,
  IconTrash,
} from "@/components/icons";
import { ModaleAjoutActif } from "@/components/ModaleAjoutActif";
import { api } from "@/lib/api";
import { depuis, pluriel, tronquer } from "@/lib/format";
import type { ActifDuFeed, ActionHistorique, FeedItem, RenseignementsStats } from "@/lib/types";

const CRITICITES = [
  ["", "Toutes"],
  ["critique", "Critique"],
  ["elevee", "Élevée"],
  ["moyenne", "Moyenne"],
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
  onAjoute,
}: {
  actifs: ActifDuFeed[];
  actifSel: number | null;
  triActifs: string;
  lien: (p: Record<string, string | number | null>) => string;
  onAjoute: () => void;
}) {
  const [recherche, setRecherche] = useState("");
  const [ajout, setAjout] = useState(false);
  const filtres = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return q ? actifs.filter((a) => a.libelle.toLowerCase().includes(q)) : actifs;
  }, [actifs, recherche]);

  const technique = filtres.filter((a) => a.type === "technique");
  const normatif = filtres.filter((a) => a.type === "normatif");

  // Arborescence : le tronc vertical est le border-l du groupe (cf. plus
  // bas) — un div ne s'etend que sur la hauteur de son contenu, donc il
  // s'arrete naturellement apres la derniere ligne sans logique separee.
  // Chaque ligne ajoute juste son coude horizontal ("├─"/"└─" visuel).
  const ligne = (a: ActifDuFeed) => {
    const sel = actifSel === a.id;
    return (
      <div key={a.id} className="tree-actif-noeud relative pl-4">
        <span className="pointer-events-none absolute top-1/2 left-0 h-px w-[9px] bg-border" />
        <Link
          href={lien({ actif: a.id })}
          className={`relative flex items-center gap-2.5 rounded-lg px-[9px] py-[9px] text-[13px] transition-colors ${
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
      </div>
    );
  };

  const groupe = (titre: string, couleur: string) => (
    <div className="tree-groupe-titre flex items-center gap-2 px-[11px] pt-5 pb-2 font-display text-[13px] font-bold tracking-[0.04em] text-tree-titre uppercase">
      <span className="size-[7px] shrink-0 rounded-full" style={{ background: couleur }} />
      {titre}
    </div>
  );

  return (
    <Side
      titre="Actifs"
      action={
        <button
          type="button"
          onClick={() => setAjout(true)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-accent bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink hover:brightness-110"
        >
          <IconPlus className="size-3" />
          Ajouter
        </button>
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

      {groupe("Technique", "var(--color-statut-demarre)")}
      <div className="tree-groupe ml-[15px] border-l border-border">
        {technique.length ? (
          technique.map((a) => ligne(a))
        ) : (
          <span className="block px-[11px] py-[9px] text-xs text-ink-faint italic">
            Aucun actif technique
          </span>
        )}
      </div>

      {groupe("Normatif", "var(--color-faib)")}
      <div className="tree-groupe ml-[15px] border-l border-border">
        {normatif.length ? (
          normatif.map((a) => ligne(a))
        ) : (
          <span className="block px-[11px] py-[9px] text-xs text-ink-faint italic">
            Aucun référentiel
          </span>
        )}
      </div>

      <ModaleAjoutActif
        ouvert={ajout}
        onFermer={() => setAjout(false)}
        onAjoute={onAjoute}
      />
    </Side>
  );
}

/** Une carte de la liste : le texte tronque se deplie en place au clic
 * (sans naviguer) et montre alors le texte complet + tout ce qu'on connait
 * en plus du renseignement — la Source mise en avant, et les champs
 * d'enrichissement s'ils sont renseignes. Le reste de la carte reste un
 * lien classique vers la fiche detail. */
function CarteRenseignement({ item }: { item: FeedItem }) {
  const { renseignement: r, traitement: t, match } = item;
  const [ouvert, setOuvert] = useState(false);
  const long = r.description.length > 210;

  const bascule = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setOuvert((v) => !v);
  };

  const enrichissement: { label: string; valeur: string }[] = [
    r.auteur && { label: "Auteur", valeur: r.auteur },
    r.niveau_confiance && { label: "Niveau de confiance", valeur: r.niveau_confiance_label },
    r.secteur_concerne && { label: "Secteur concerné", valeur: r.secteur_concerne },
    r.tlp && { label: "TLP", valeur: r.tlp.toUpperCase() },
    r.tags.length > 0 && { label: "Tags", valeur: r.tags.join(", ") },
    r.cve_associees.length > 0 && { label: "CVE associées", valeur: r.cve_associees.join(", ") },
    r.ioc_associees.length > 0 && { label: "IOC associées", valeur: r.ioc_associees.join(", ") },
  ].filter(Boolean) as { label: string; valeur: string }[];

  return (
    <Link
      href={`/app/renseignements/${r.id}`}
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
        <span className="shrink-0 font-mono text-[11.5px] text-ink-faint">{depuis(r.decouvert_le)}</span>
      </div>

      {/* span, pas button : deja imbrique dans le <Link> de la carte, deux
         elements interactifs imbriques (bouton dans un lien) seraient du
         HTML invalide. */}
      <span
        role={long ? "button" : undefined}
        tabIndex={long ? 0 : undefined}
        onClick={long ? bascule : undefined}
        onKeyDown={
          long
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") bascule(e as unknown as React.MouseEvent);
              }
            : undefined
        }
        className={`mt-2 block text-[13px] leading-relaxed text-ink-soft ${long ? "cursor-pointer hover:text-ink" : ""}`}
      >
        {ouvert ? r.description : tronquer(r.description, 210)}
        {long && (
          <span className="ml-1.5 inline-flex items-center gap-0.5 align-middle text-[11.5px] font-semibold text-accent">
            {ouvert ? "Réduire" : "Lire la suite"}
            <IconChevron className={`size-3 transition-transform ${ouvert ? "rotate-180" : ""}`} />
          </span>
        )}
      </span>

      {ouvert && (
        <div className="renseignement-enrichissement mt-3 rounded-xl border border-border bg-surface-2 px-3.5 py-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded-[5px] bg-accent-soft px-2 py-0.5 font-mono text-[10.5px] font-semibold tracking-[0.06em] text-accent uppercase">
              Source
            </span>
            <span className="text-[12.5px] font-medium text-ink">{r.source}</span>
            {r.url_source && (
              // span, pas <a> : deja imbrique dans le <Link> de la carte, un
              // lien dans un lien serait du HTML invalide (meme raison que
              // "Lire la suite" plus haut).
              <span
                role="link"
                tabIndex={0}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  window.open(r.url_source, "_blank", "noopener,noreferrer");
                }}
                onKeyDown={(e) => {
                  if (e.key !== "Enter" && e.key !== " ") return;
                  e.preventDefault();
                  e.stopPropagation();
                  window.open(r.url_source, "_blank", "noopener,noreferrer");
                }}
                className="cursor-pointer text-[11.5px] text-accent hover:underline"
              >
                Voir l&apos;avis d&apos;origine →
              </span>
            )}
          </div>
          {enrichissement.length > 0 ? (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {enrichissement.map((e) => (
                <div key={e.label} className="min-w-0">
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.07em] text-ink-faint uppercase">
                    {e.label}
                  </dt>
                  <dd className="truncate text-[12.5px] text-ink-soft">{e.valeur}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-[11.5px] text-ink-faint italic">
              Aucune information complémentaire fournie par la source pour ce renseignement.
            </p>
          )}
        </div>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-2.5">
        <span className="font-mono text-[11.5px] font-medium text-accent">{r.source}</span>
        <NatureTag nature={r.nature} label={r.nature_label} />
        {r.cvss_score !== null && (
          <span className="font-mono text-[11.5px] text-ink-faint">CVSS {r.cvss_score.toFixed(1)}</span>
        )}
        {t ? (
          <StatusPill statut={t.statut} label={t.statut_label} />
        ) : (
          <StatusPill statut="a_traiter" label="+ Traitement" />
        )}
        {match && <ConfBar palier={match.palier} pourcent={match.pourcent} />}
      </div>
    </Link>
  );
}

const FILTRES_HISTORIQUE = [
  ["", "Tout"],
  ["actif", "Actifs"],
  ["traitement", "Traitements"],
] as const;

const ICONE_TYPE: Record<string, React.ReactNode> = {
  actif: <IconServer className="size-3" />,
  traitement: <IconClipboard className="size-3" />,
};

const ICONE_ACTION: Record<string, { icone: React.ReactNode; couleur: string }> = {
  ajout: { icone: <IconPlus className="size-3" />, couleur: "bg-faib-soft text-faib" },
  modification: { icone: <IconRefresh className="size-3" />, couleur: "bg-accent-soft text-accent" },
  suppression: { icone: <IconTrash className="size-3" />, couleur: "bg-crit-soft text-crit" },
};

/** Panneau "Historique des actions" — journal unifie Actifs + Traitements,
 * le plus recent en premier (deja trie ainsi cote API), avec un filtre par
 * type d'evenement. Widget autonome : sa propre pagination (charger plus),
 * independante des filtres de la liste de renseignements a cote. */
function PanneauHistorique() {
  const [type, setType] = useState("");
  const [items, setItems] = useState<ActionHistorique[] | null>(null);
  const [plusDisponible, setPlusDisponible] = useState(true);
  const LIMITE = 20;

  const charger = useCallback((decalage: number, remplacer: boolean) => {
    api
      .journal({ type: type || undefined, decalage, limite: LIMITE })
      .then((nouveaux) => {
        setPlusDisponible(nouveaux.length === LIMITE);
        setItems((prev) => (remplacer || !prev ? nouveaux : [...prev, ...nouveaux]));
      })
      .catch(() => setItems((prev) => prev ?? []));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type]);

  useEffect(() => {
    setItems(null);
    charger(0, true);
  }, [type, charger]);

  return (
    <aside className="historique-panneau w-[280px] shrink-0 rounded-2xl border border-border bg-surface shadow-card max-xl:hidden">
      <div className="border-b border-border px-4 py-3.5">
        <h2 className="font-display text-[13.5px] font-bold tracking-tight">Historique des actions</h2>
        <p className="mt-0.5 text-[11px] text-ink-faint">
          Ajouts, modifications, suppressions — actifs et traitements.
        </p>
        <div className="mt-2.5 flex gap-1.5">
          {FILTRES_HISTORIQUE.map(([v, label]) => (
            <button
              key={v || "tout"}
              type="button"
              onClick={() => setType(v)}
              className={`flex-1 rounded-full border px-1 py-[5px] text-center text-[10.5px] font-semibold ${
                type === v
                  ? "border-accent-line bg-accent-soft text-accent"
                  : "border-border bg-surface-2 text-ink-soft hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-h-[560px] overflow-y-auto">
        {items === null ? (
          <div className="px-4 py-6">
            <Spinner />
          </div>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-center text-[12px] text-ink-faint italic">
            Aucune action enregistrée pour l&apos;instant.
          </p>
        ) : (
          <>
            {items.map((h) => {
              const a = ICONE_ACTION[h.action];
              return (
                <div key={h.id} className="flex gap-2.5 border-b border-border px-4 py-3 last:border-b-0">
                  <span
                    className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md ${a.couleur}`}
                  >
                    {a.icone}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
                      {ICONE_TYPE[h.type_objet]}
                      <span className="font-semibold uppercase tracking-[0.04em]">{h.action_label}</span>
                      <span>· {h.type_objet_label}</span>
                    </div>
                    <p className="mt-0.5 truncate text-[12.5px] font-medium text-ink" title={h.objet_repr}>
                      {h.objet_repr}
                    </p>
                    {h.detail && <p className="mt-0.5 truncate text-[11px] text-ink-soft">{h.detail}</p>}
                    <div className="mt-1 flex items-center gap-1.5 font-mono text-[10.5px] text-ink-faint">
                      <span>{depuis(h.horodatage)}</span>
                      {h.utilisateur && <span>· {h.utilisateur}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
            {plusDisponible && (
              <button
                type="button"
                onClick={() => charger(items.length, false)}
                className="block w-full py-2.5 text-center text-[11.5px] font-semibold text-accent hover:underline"
              >
                Charger plus
              </button>
            )}
          </>
        )}
      </div>
    </aside>
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
  const [stats, setStats] = useState<RenseignementsStats | null>(null);
  const [actifs, setActifs] = useState<ActifDuFeed[]>([]);

  const chargerFeed = useCallback(() => {
    setItems(null);
    setStats(null);
    api
      .feed({ actif: actifSel ?? undefined, criticite: criticite || undefined, tri })
      .then((r) => {
        setItems(r.items);
        setStats(r.stats);
      })
      .catch(() => {
        setItems([]);
        setStats(null);
      });
  }, [actifSel, criticite, tri]);

  useEffect(chargerFeed, [chargerFeed]);

  const chargerActifs = useCallback(() => {
    api.actifsDuFeed(triActifs).then(setActifs).catch(() => setActifs([]));
  }, [triActifs]);

  useEffect(chargerActifs, [chargerActifs]);

  /** Construit une URL en conservant les autres filtres. */
  const lien = (modifs: Record<string, string | number | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(modifs)) {
      if (v === null || v === "") p.delete(k);
      else p.set(k, String(v));
    }
    const s = p.toString();
    return `/app/renseignements${s ? `?${s}` : ""}`;
  };

  // Ces 4 chiffres viennent de `stats` (calcule serveur AVANT le filtre
  // criticite/statut) : ils decrivent le perimetre choisi (l'actif, ou tout
  // le client) dans son ensemble, jamais la liste `items` deja filtree —
  // c'est ce qui garantit qu'ils ne bougent pas quand on change de criticite.
  const nbTotal = stats?.nb_renseignements ?? items?.length ?? "—";
  const nbATraiter = stats?.par_etape.a_traiter ?? 0;
  const nbCritiques = stats?.par_criticite_ouverts.critique ?? 0;
  const nbNouveaux = stats?.nb_non_consultes ?? 0;

  const libelleActif = actifs.find((a) => a.id === actifSel)?.libelle;

  return (
    <AppShell
      side={
        <ColonneActifs
          actifs={actifs}
          actifSel={actifSel}
          triActifs={triActifs}
          lien={lien}
          onAjoute={chargerActifs}
        />
      }
    >
      <PageHead
        titre="Renseignements"
        sous={
          <>
            Filtré sur vos actifs déclarés. Le flux complet est dans{" "}
            <Link href="/app/actualites" className="text-accent">
              Actualités
            </Link>
            .
          </>
        }
        stats={
          <>
            <Stat valeur={nbTotal} label="Total" />
            <Stat ton="gold" valeur={nbATraiter} label="À traiter" />
            <Stat ton="crit" valeur={nbCritiques} label="Critiques" />
            <Stat ton="accent" valeur={nbNouveaux} label="Nouveaux" />
          </>
        }
      />

      <div className="renseignements-barre-filtres flex flex-wrap items-center gap-[7px]">
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

      <div className="renseignements-corps flex items-start gap-5">
        <div className="min-w-0 flex-1">
          {items === null ? (
            <Spinner />
          ) : (
            <>
              <div className="flex items-baseline gap-2.5">
                <span className="tabular font-mono text-[19px] font-semibold">{items.length}</span>
                <span className="text-[13px] text-ink-soft">{libelleActif ?? "Tous les actifs"}</span>
              </div>

              {items.length ? (
                <div className="renseignements-liste mt-3 flex flex-col gap-3">
                  {items.map((item) => (
                    <CarteRenseignement key={item.renseignement.id} item={item} />
                  ))}
                </div>
              ) : (
                <Card className="mt-3">
                  <Empty
                    icone={<IconShield />}
                    action={
                      !actifs.length ? (
                        <Link
                          href="/app/actifs"
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
                        <Link href="/app/actualites" className="text-accent">
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
        </div>

        <PanneauHistorique />
      </div>
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
