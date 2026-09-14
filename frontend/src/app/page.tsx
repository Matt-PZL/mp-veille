"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell, PageHead } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import {
  Bar,
  Card,
  CardHead,
  Empty,
  SevDot,
  Spinner,
  StatusPill,
  CheckPastille,
  TON_KPI,
} from "@/components/ui";
import {
  IconAlert,
  IconBars,
  IconCalendar,
  IconCheck,
  IconNews,
  IconPlus,
  IconRefresh,
  IconServer,
  IconShield,
} from "@/components/icons";
import { api } from "@/lib/api";
import { dateCourte, depuis, pluriel, tronquer } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

/* ------------------------------------------------------------------ */
/* Tuiles de Monitoring — compactes, pour caser 9 chiffres sans que la
   section ne domine la page (retour client : trop de place pour peu de
   texte). Deux formes : une tuile simple (icone + libelle + valeur), et une
   paire de mini-lignes empilees dans le meme volume qu'une tuile simple
   (ex : Actifs clean / Actifs a risque, l'un sur l'autre).             */
/* ------------------------------------------------------------------ */
function TuileSimple({
  ton,
  icone,
  label,
  valeur,
  href,
}: {
  ton: keyof typeof TON_KPI;
  icone: React.ReactNode;
  label: string;
  valeur: number | string;
  href: string;
}) {
  const t = TON_KPI[ton];
  return (
    <Link
      href={href}
      className="flex flex-col justify-between gap-2.5 rounded-xl border border-border bg-surface px-3.5 py-3 shadow-card transition-colors hover:border-border-strong hover:bg-surface-2"
    >
      <div className="flex items-center gap-2">
        <span
          className={`flex size-6 shrink-0 items-center justify-center rounded-md [&_svg]:size-3 ${t.fond} ${t.texte}`}
        >
          {icone}
        </span>
        <span className="min-w-0 truncate text-[11.5px] font-medium text-ink-soft">{label}</span>
      </div>
      <div className={`tabular font-mono text-[22px] leading-none font-semibold ${t.valeur}`}>{valeur}</div>
    </Link>
  );
}

function MiniLigne({
  ton,
  label,
  valeur,
  href,
}: {
  ton: keyof typeof TON_KPI;
  label: string;
  valeur: number | string;
  href: string;
}) {
  const t = TON_KPI[ton];
  return (
    <Link
      href={href}
      className="flex flex-1 items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-[7px] shadow-card transition-colors hover:border-border-strong hover:bg-surface-2"
    >
      <span className="min-w-0 truncate text-[11px] font-medium text-ink-soft">{label}</span>
      <span className={`tabular shrink-0 font-mono text-[15px] font-semibold ${t.valeur}`}>{valeur}</span>
    </Link>
  );
}

function TuilePaire({
  haut,
  bas,
}: {
  haut: { ton: keyof typeof TON_KPI; label: string; valeur: number | string; href: string };
  bas: { ton: keyof typeof TON_KPI; label: string; valeur: number | string; href: string };
}) {
  return (
    <div className="flex flex-col gap-[5px]">
      <MiniLigne {...haut} />
      <MiniLigne {...bas} />
    </div>
  );
}

const LIBELLES_ETAPES: Record<string, { titre: string; lien: string; action: string }> = {
  actifs: {
    titre: "Déclarez vos actifs",
    lien: "/actifs",
    action: "Compléter l'inventaire",
  },
  referentiels: {
    titre: "Choisissez vos référentiels",
    lien: "/actifs?type=normatif",
    action: "Sélectionner",
  },
  traitement: {
    titre: "Traitez un renseignement",
    lien: "/renseignements",
    action: "Voir les renseignements",
  },
};

function Demarrage({ d, onMasquer }: { d: Dashboard; onMasquer: () => void }) {
  const restant = d.onboarding.filter((e) => !e.fait).length;

  const detail = (cle: string, fait: boolean) => {
    if (cle === "actifs") {
      return fait
        ? `${d.nb_actifs_technique} actif${pluriel(d.nb_actifs_technique)} technique${pluriel(d.nb_actifs_technique)} déclaré${pluriel(d.nb_actifs_technique)}. Un parc d'entreprise en compte généralement 15 à 40.`
        : "Aucun actif technique déclaré. Cherchez votre produit par son nom dans un catalogue de référence.";
    }
    if (cle === "referentiels") {
      return fait
        ? `${d.nb_referentiels} référentiel${pluriel(d.nb_referentiels)} suivi${pluriel(d.nb_referentiels)}.`
        : "ISO 27001, RGPD, NIS2, DORA. C'est ce qui alimente le volet normatif de votre veille.";
    }
    return "Statut, justificatif, échéance. Chaque décision horodatée devient votre preuve d'audit ISO 27001.";
  };

  return (
    <section className="relative overflow-hidden rounded-2xl border border-accent-line bg-surface px-6 py-[22px] after:pointer-events-none after:absolute after:inset-0 after:bg-[radial-gradient(90%_140%_at_100%_0%,var(--color-accent-soft)_0%,transparent_62%)] after:content-['']">
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[17px] font-bold tracking-tight">
            Finissez votre mise en route
          </h2>
          <p className="mt-1 max-w-[70ch] text-[13.5px] text-ink-soft">
            La veille ne remonte que ce qui touche vos actifs déclarés. Plus votre inventaire est
            complet, moins vous passez à côté. Il reste {restant} étape{pluriel(restant)}.
          </p>
        </div>
        <button
          type="button"
          onClick={onMasquer}
          className="shrink-0 text-[12.5px] text-ink-faint underline hover:text-ink"
        >
          Masquer
        </button>
      </div>

      <div className="relative z-10 mt-5 grid gap-3.5 md:grid-cols-3">
        {d.onboarding.map((etape, i) => {
          const l = LIBELLES_ETAPES[etape.cle];
          return (
            <div
              key={etape.cle}
              className={`flex flex-col gap-2.5 rounded-xl border p-4 ${
                etape.fait ? "border-faib bg-faib-soft" : "border-border bg-surface-2"
              }`}
            >
              {etape.fait ? (
                <CheckPastille />
              ) : (
                <span className="flex size-6 items-center justify-center rounded-lg bg-accent-soft font-mono text-xs font-semibold text-accent">
                  {i + 1}
                </span>
              )}
              <b className="text-sm font-semibold">{l.titre}</b>
              <p className="flex-1 text-[12.5px] text-ink-soft">{detail(etape.cle, etape.fait)}</p>
              <Link
                href={l.lien}
                className={`text-[12.5px] font-semibold ${etape.fait ? "text-faib" : "text-accent"}`}
              >
                {l.action} →
              </Link>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Contenu() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [masque, setMasque] = useState(false);

  useEffect(() => {
    api.dashboard().then(setD).catch((e) => setErreur(e.message));
    try {
      setMasque(!!localStorage.getItem("veille-demarrage-masque"));
    } catch {}
  }, []);

  const masquer = useCallback(() => {
    setMasque(true);
    try {
      localStorage.setItem("veille-demarrage-masque", "1");
    } catch {}
  }, []);

  if (erreur) {
    return (
      <Card>
        <Empty icone={<IconAlert />}>{erreur}</Empty>
      </Card>
    );
  }
  if (!d) return <Spinner />;

  const aTraiter = d.par_etape.a_traiter ?? 0;

  return (
    <AppShell
      derniereCollecte={d.derniere_collecte}
    >
      <PageHead
        titre="Vue d'ensemble"
        sous={
          d.nb_renseignements ? (
            <>
              <b className="font-mono font-medium text-ink">{d.nb_renseignements}</b> renseignement
              {pluriel(d.nb_renseignements)} concerne{pluriel(d.nb_renseignements)} vos actifs —{" "}
              <b className="font-mono font-medium text-ink">{aTraiter}</b> attend
              {aTraiter > 1 ? "ent" : ""} une décision.
            </>
          ) : (
            "Aucun renseignement ne concerne encore vos actifs déclarés."
          )
        }
        actions={
          <>
            <Link
              href="/actualites"
              className="inline-flex items-center gap-[7px] rounded-lg border border-border bg-surface-2 px-[15px] py-2 text-[13px] font-semibold text-ink-soft transition-colors hover:bg-surface-3 hover:text-ink"
            >
              <IconNews className="size-3.5" />
              Voir tout le flux
            </Link>
            <Link
              href="/actifs"
              className="inline-flex items-center gap-[7px] rounded-lg border border-accent bg-accent px-[15px] py-2 text-[13px] font-semibold text-accent-ink transition-[filter] hover:brightness-110"
            >
              <IconPlus className="size-3.5" />
              Ajouter un actif
            </Link>
          </>
        }
      />

      {!d.onboarding_termine && !masque && <Demarrage d={d} onMasquer={masquer} />}

      {/* Monitoring : deux blocs cote a cote — Actifs/Renseignements a
         gauche (mix tuiles simples + paires empilees), repartition par
         criticite en 2x2 a droite. Disposition et regroupement decides avec
         le client. Chiffres tous issus de calculer_perimetre_stats() cote
         API : jamais de recalcul local ici. Tuiles volontairement
         compactes (retour client : trop de place pour peu de texte). */}
      <div className="monitoring-tuiles grid gap-3.5 lg:grid-cols-2">
        <div className="grid grid-cols-2 gap-2.5">
          <TuileSimple ton="neutre" icone={<IconServer />} label="Total Actifs" valeur={d.nb_actifs} href="/actifs" />
          <TuilePaire
            haut={{ ton: "faib", label: "Actifs clean", valeur: d.nb_actifs_clean, href: "/actifs?etat=clean" }}
            bas={{
              ton: "gold",
              label: "Actifs à risque",
              valeur: d.nb_actifs_avec_non_traites,
              href: "/actifs?etat=non_traite",
            }}
          />
          <TuileSimple
            ton="accent"
            icone={<IconShield />}
            label="Total Renseignements"
            valeur={d.nb_renseignements}
            href="/renseignements"
          />
          <TuilePaire
            haut={{
              ton: "faib",
              label: "Renseignements traités",
              valeur: d.nb_renseignements - d.nb_ouverts,
              href: "/renseignements?statut=clos,non_applicable",
            }}
            bas={{
              ton: "gold",
              label: "Renseignements non traités",
              valeur: d.nb_ouverts,
              href: "/renseignements?statut=a_traiter,en_cours",
            }}
          />
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <TuileSimple
            ton="crit"
            icone={<IconAlert />}
            label="Critiques"
            valeur={d.par_criticite_ouverts.critique ?? 0}
            href="/renseignements?criticite=critique&statut=a_traiter,en_cours"
          />
          <TuileSimple
            ton="elev"
            icone={<IconBars />}
            label="Élevées"
            valeur={d.par_criticite_ouverts.elevee ?? 0}
            href="/renseignements?criticite=elevee&statut=a_traiter,en_cours"
          />
          <TuileSimple
            ton="moy"
            icone={<IconBars />}
            label="Moyens"
            valeur={d.par_criticite_ouverts.moyenne ?? 0}
            href="/renseignements?criticite=moyenne&statut=a_traiter,en_cours"
          />
          <TuileSimple
            ton="faib"
            icone={<IconBars />}
            label="Faible"
            valeur={d.par_criticite_ouverts.faible ?? 0}
            href="/renseignements?criticite=faible&statut=a_traiter,en_cours"
          />
        </div>
      </div>

      <div className="grid gap-3.5 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHead
            titre="À traiter en priorité"
            couleurPoint="var(--color-crit)"
            action={<Link href="/renseignements" className="hover:text-accent">Tout voir</Link>}
          />
          <div className="flex flex-1 flex-col">
            {d.prioritaires.length ? (
              d.prioritaires.map((r) => (
                <Link
                  key={r.id}
                  href={`/renseignements/${r.id}`}
                  className="flex items-center gap-3 border-b border-border px-[18px] py-[11px] text-[13px] last:border-b-0 hover:bg-surface-2"
                >
                  <SevDot criticite={r.criticite} />
                  <span className="shrink-0 font-mono text-xs text-ink-soft">
                    {r.reference || r.source}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{tronquer(r.titre, 64)}</span>
                  <StatusPill statut="a_traiter" label="À traiter" />
                </Link>
              ))
            ) : (
              <Empty icone={<IconCheck />}>Aucun renseignement à prioriser.</Empty>
            )}
          </div>
        </Card>

        <Card className="lg:col-span-5">
          <CardHead titre="Avancement du traitement" couleurPoint="var(--color-accent)" />
          <div className="flex-1 px-[18px] py-4">
            <div className="flex flex-col gap-3">
              <Bar label="À traiter" valeur={aTraiter} total={d.nb_renseignements} couleur="var(--color-gold)" />
              <Bar label="Démarré" valeur={d.par_etape.en_cours ?? 0} total={d.nb_renseignements} couleur="var(--color-accent)" />
              <Bar label="Clos" valeur={d.par_etape.clos ?? 0} total={d.nb_renseignements} couleur="var(--color-faib)" />
              <Bar label="Non applicable" valeur={d.par_etape.non_applicable ?? 0} total={d.nb_renseignements} couleur="var(--color-ink-faint)" />
            </div>
            <p className="mt-[18px] text-[12.5px] leading-relaxed text-ink-faint">
              {d.taux_cloture !== null ? (
                <>
                  {d.taux_cloture} % des traitements sont clos
                  {d.delai_moyen_jours ? `, en ${d.delai_moyen_jours} jours en moyenne` : ""}.
                </>
              ) : (
                "Aucun renseignement n'a encore été pris en charge. Un traitement clos avec justificatif constitue votre trace d'audit."
              )}
            </p>
          </div>
        </Card>

        <Card className="lg:col-span-8">
          <CardHead
            titre="Activité de collecte"
            couleurPoint="var(--color-faib)"
            action={<span className="font-mono">6 dernières semaines</span>}
          />
          <div className="flex-1 px-[18px] py-4">
            <div className="flex h-[116px] items-end gap-2 pt-[22px]">
              {d.activite.map((a) => {
                const haut = a.n === d.activite_max && a.n > 0;
                return (
                  <div
                    key={a.label}
                    title={`${a.label} — ${a.n} renseignement${pluriel(a.n)}`}
                    className="group relative flex h-full flex-1 flex-col justify-end"
                  >
                    <span
                      className={`tabular absolute -top-[19px] right-0 left-0 text-center font-mono text-[11px] font-medium ${haut ? "text-accent" : "text-ink-faint"}`}
                    >
                      {a.n}
                    </span>
                    <span
                      className={`min-h-[3px] w-full rounded-t-[5px] rounded-b-[3px] transition-[filter] group-hover:brightness-125 ${
                        haut
                          ? "bg-[linear-gradient(180deg,var(--color-accent)_0%,var(--color-accent-soft)_100%)]"
                          : "bg-surface-3"
                      }`}
                      style={{ height: `${Math.round((a.n / d.activite_max) * 100)}%` }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="mt-2 flex gap-2">
              {d.activite.map((a) => (
                <span key={a.label} className="flex-1 text-center font-mono text-[10.5px] text-ink-faint">
                  {a.label}
                </span>
              ))}
            </div>
          </div>
        </Card>

        <Card className="lg:col-span-4">
          <CardHead
            titre="Santé de la surveillance"
            couleurPoint={
              d.sante.some((s) => s.niveau === "warn") ? "var(--color-gold)" : "var(--color-faib)"
            }
          />
          <div className="flex flex-1 flex-col">
            {d.sante.map((s, i) => (
              <div key={i} className="flex gap-3 border-b border-border px-[18px] py-3 text-[13px] last:border-b-0">
                <span
                  className={`mt-px flex size-[21px] shrink-0 items-center justify-center rounded-full [&_svg]:size-[11px] ${
                    s.niveau === "ok" ? "bg-faib-soft text-faib" : "bg-gold-soft text-gold"
                  }`}
                >
                  {s.niveau === "ok" ? <IconCheck /> : <IconAlert />}
                </span>
                <span className="min-w-0">
                  {s.titre}
                  <small className="mt-0.5 block text-[11.5px] leading-relaxed text-ink-faint">
                    {s.detail}
                  </small>
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-6">
          <CardHead
            titre="Échéances à venir"
            couleurPoint="var(--color-accent)"
            action={<span className="font-mono">7 prochains jours</span>}
          />
          <div className="flex flex-1 flex-col">
            {d.echeances.length ? (
              d.echeances.map((e) => (
                <Link
                  key={e.id_renseignement}
                  href={`/renseignements/${e.id_renseignement}`}
                  className="flex items-center gap-3 border-b border-border px-[18px] py-[11px] text-[13px] last:border-b-0 hover:bg-surface-2"
                >
                  <span className="min-w-0 flex-1 truncate">
                    {e.actif} — {tronquer(e.titre, 44)}
                  </span>
                  <span className="shrink-0 rounded-[5px] border border-gold bg-gold-soft px-2 py-px font-mono text-[10.5px] font-semibold text-gold">
                    {dateCourte(e.echeance)}
                  </span>
                </Link>
              ))
            ) : (
              <Empty icone={<IconCalendar />}>Aucune échéance dans les 7 prochains jours.</Empty>
            )}
          </div>
        </Card>

        <Card className="lg:col-span-6">
          <CardHead
            titre="Derniers renseignements"
            couleurPoint="var(--color-ink-faint)"
            action={<Link href="/renseignements" className="hover:text-accent">Tout voir</Link>}
          />
          <div className="flex flex-1 flex-col">
            {d.derniers.length ? (
              d.derniers.map((r) => (
                <Link
                  key={r.id}
                  href={`/renseignements/${r.id}`}
                  className="flex items-center gap-3 border-b border-border px-[18px] py-[11px] text-[13px] last:border-b-0 hover:bg-surface-2"
                >
                  <SevDot criticite={r.criticite} />
                  <span className="shrink-0 font-mono text-xs text-ink-soft">
                    {r.reference || r.source}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{tronquer(r.titre, 48)}</span>
                  <span className="ml-auto shrink-0 font-mono text-[11.5px] text-ink-faint">
                    {depuis(r.decouvert_le)}
                  </span>
                </Link>
              ))
            ) : (
              <Empty icone={<IconRefresh />}>
                Aucun renseignement — l&apos;ingestion n&apos;a pas encore tourné.
              </Empty>
            )}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

export default function PageDashboard() {
  return (
    <Garde>
      <Contenu />
    </Garde>
  );
}
