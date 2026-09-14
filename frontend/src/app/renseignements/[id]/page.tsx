"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import {
  Button,
  Card,
  CardHead,
  Empty,
  ErreurChamp,
  Input,
  Label,
  Modal,
  NatureTag,
  SevDot,
  Spinner,
  StatusPill,
  Textarea,
} from "@/components/ui";
import { IconAlert, IconChevron, IconDownload, IconPlus } from "@/components/icons";
import { ApiError, api } from "@/lib/api";
import { dateLongue } from "@/lib/format";
import type { RenseignementDetail, Statut } from "@/lib/types";

const STATUTS: { code: Statut; label: string; actif: string }[] = [
  { code: "a_traiter", label: "À traiter", actif: "border-gold bg-gold text-[#1A1200]" },
  { code: "en_cours", label: "Démarré", actif: "border-accent bg-accent text-accent-ink" },
  { code: "clos", label: "Clos", actif: "border-faib bg-faib text-[#04170A]" },
  { code: "non_applicable", label: "Non applicable", actif: "border-ink-faint bg-ink-faint text-bg" },
];

function Formulaire({ d, onEnregistre }: { d: RenseignementDetail; onEnregistre: () => void }) {
  const t = d.traitement;
  const [statut, setStatut] = useState<Statut>(t?.statut ?? "a_traiter");
  const [planAction, setPlanAction] = useState(t?.plan_action ?? "");
  const [justificatif, setJustificatif] = useState(t?.justificatif ?? "");
  const [echeance, setEcheance] = useState(t?.echeance ?? "");
  const [cab, setCab] = useState<boolean | null>(t?.passage_cab ?? null);
  const [fichier, setFichier] = useState<File | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const montreDemarrage = statut === "en_cours";
  const montreJustificatif = statut === "clos" || statut === "non_applicable";
  const montreFichier = statut === "clos";

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setErreurs({});
    setEnvoi(true);
    try {
      const fd = new FormData();
      fd.append("statut", statut);
      fd.append("justificatif", justificatif);
      fd.append("plan_action", planAction);
      if (echeance) fd.append("echeance", echeance);
      if (cab !== null) fd.append("passage_cab", String(cab));
      if (fichier) fd.append("preuve_fichier", fichier);

      await api.enregistrerTraitement(d.renseignement.id, fd);
      onEnregistre();
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.erreurs).length) setErreurs(err.erreurs);
      else setErreurs({ statut: err instanceof Error ? err.message : "Échec de l'enregistrement." });
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <form onSubmit={soumettre}>
      <div className="mb-5 flex flex-wrap gap-[7px]">
        {STATUTS.map((s) => (
          <button
            key={s.code}
            type="button"
            onClick={() => setStatut(s.code)}
            className={`min-w-[130px] flex-1 rounded-lg border px-2 py-[11px] text-[13px] font-semibold transition-colors ${
              statut === s.code
                ? s.actif
                : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <ErreurChamp>{erreurs.statut}</ErreurChamp>

      <Card className="p-[22px]">
        {montreDemarrage && (
          <>
            <div className="mb-5">
              <label className="mb-[7px] block text-[13px] font-semibold">
                Plan d&apos;action<span className="ml-[3px] text-crit">*</span>
              </label>
              <Textarea
                value={planAction}
                onChange={(e) => setPlanAction(e.target.value)}
                placeholder="Décrire les actions prévues pour traiter ce renseignement…"
              />
              <ErreurChamp>{erreurs.plan_action}</ErreurChamp>
            </div>
            <div className="mb-5">
              <label className="mb-[7px] block text-[13px] font-semibold">
                Date prévisionnelle<span className="ml-[3px] text-crit">*</span>
              </label>
              <Input type="date" value={echeance ?? ""} onChange={(e) => setEcheance(e.target.value)} />
              <ErreurChamp>{erreurs.echeance}</ErreurChamp>
            </div>
            <div className="mb-5">
              <label className="mb-[7px] block text-[13px] font-semibold">
                Passage en CAB nécessaire ?<span className="ml-[3px] text-crit">*</span>
              </label>
              <div className="flex gap-2">
                {[
                  [true, "Oui"],
                  [false, "Non"],
                ].map(([v, label]) => (
                  <button
                    key={String(v)}
                    type="button"
                    onClick={() => setCab(v as boolean)}
                    className={`flex-1 rounded-lg border py-[9px] text-[12.5px] font-semibold transition-colors ${
                      cab === v
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
                    }`}
                  >
                    {label as string}
                  </button>
                ))}
              </div>
              <ErreurChamp>{erreurs.passage_cab}</ErreurChamp>
            </div>
          </>
        )}

        {montreJustificatif && (
          <div className="mb-5">
            <label className="mb-[7px] block text-[13px] font-semibold">
              Justificatif<span className="ml-[3px] text-crit">*</span>
            </label>
            <Textarea
              value={justificatif}
              onChange={(e) => setJustificatif(e.target.value)}
              placeholder="Preuve textuelle : ce qui a été fait, pourquoi ce renseignement est clos ou non applicable…"
            />
            <ErreurChamp>{erreurs.justificatif}</ErreurChamp>
          </div>
        )}

        {montreFichier && (
          <div className="mb-5">
            <label className="mb-[7px] block text-[13px] font-semibold">
              Preuve fichier <span className="text-[11.5px] font-normal text-ink-faint">(optionnel)</span>
            </label>
            {t?.preuve_fichier_url && (
              <p className="mb-2 text-[12.5px] text-ink-soft">
                Fichier actuel :{" "}
                <a href={t.preuve_fichier_url} target="_blank" rel="noopener" className="text-accent">
                  voir
                </a>
              </p>
            )}
            <input
              type="file"
              onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
              className="w-full text-[13px] text-ink-soft file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border file:bg-surface-3 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-ink-soft"
            />
          </div>
        )}

        {statut === "a_traiter" && (
          <p className="mb-5 text-[12.5px] leading-relaxed text-ink-faint">
            Aucune information supplémentaire n&apos;est requise pour ce statut. Passez en
            « Démarré » pour poser un plan d&apos;action, ou en « Clos » pour fournir un justificatif.
          </p>
        )}

        <Button type="submit" variante="primaire" disabled={envoi} className="px-[22px] py-2.5">
          {envoi ? "Enregistrement…" : "Enregistrer"}
        </Button>
      </Card>
    </form>
  );
}

function Contenu() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<RenseignementDetail | null>(null);
  const [absent, setAbsent] = useState(false);
  const [modaleTraitement, setModaleTraitement] = useState(false);

  const charger = () =>
    api
      .renseignement(id)
      .then(setD)
      .catch(() => setAbsent(true));

  useEffect(() => {
    charger();
    // La consultation se marque a l'ouverture du detail : c'est ce qui fait
    // disparaitre le badge « Nouveau » cote liste.
    api.marquerConsulte(id).catch(() => {});
  }, [id]);

  if (absent) {
    return (
      <AppShell>
        <Card>
          <Empty icone={<IconAlert />}>Ce renseignement est introuvable.</Empty>
        </Card>
      </AppShell>
    );
  }
  if (!d) {
    return (
      <AppShell>
        <Spinner />
      </AppShell>
    );
  }

  const r = d.renseignement;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-[760px]">
        <Link
          href="/renseignements"
          className="mb-[18px] inline-flex items-center gap-[7px] text-[13px] text-ink-soft hover:text-ink"
        >
          <IconChevron className="size-3.5 rotate-180" />
          Retour
        </Link>

        <div
          className={`relative mb-5 overflow-hidden rounded-2xl border border-border bg-surface px-[22px] py-5 shadow-card before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:content-[''] ${
            {
              critique: "before:bg-crit",
              elevee: "before:bg-elev",
              moyenne: "before:bg-moy",
              faible: "before:bg-faib",
              "": "before:bg-ink-faint",
            }[r.criticite]
          }`}
        >
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <SevDot criticite={r.criticite} />
              <h1 className="font-display text-[17px] leading-snug font-bold tracking-tight">
                {r.reference || r.source} — {r.titre}
              </h1>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {d.traitement && <StatusPill statut={d.traitement.statut} label={d.traitement.statut_label} />}
              <Button variante="primaire" onClick={() => setModaleTraitement(true)} className="whitespace-nowrap">
                <IconPlus className="size-3.5" />
                {d.traitement ? "Modifier le traitement" : "Ajouter un traitement"}
              </Button>
            </div>
          </div>
          <p className="text-[13px] leading-relaxed text-ink-soft">{r.description}</p>

          <div className="mt-3.5 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-[6px] bg-accent-soft px-2 py-0.5">
              <span className="font-mono text-[10px] font-semibold tracking-[0.07em] text-accent uppercase">
                Source
              </span>
              {r.url_source ? (
                <a href={r.url_source} target="_blank" rel="noopener" className="text-[12px] font-semibold text-accent hover:underline">
                  {r.source} ↗
                </a>
              ) : (
                <span className="text-[12px] font-semibold text-accent">{r.source}</span>
              )}
            </span>
            <span className="font-mono text-[11.5px] text-ink-faint">{dateLongue(r.decouvert_le)}</span>
            {r.cvss_score !== null && (
              <span className="font-mono text-[11.5px] text-ink-faint">· CVSS {r.cvss_score.toFixed(1)}</span>
            )}
            <NatureTag nature={r.nature} label={r.nature_label} />
            {d.match && (
              <span
                className="font-mono text-[11.5px] text-ink-faint"
                title="Comment ce renseignement a été rattaché à un de vos actifs."
              >
                · correspondance {d.match.palier} — {d.match.pourcent} %
              </span>
            )}
          </div>
        </div>

        {(r.auteur ||
          r.niveau_confiance ||
          r.secteur_concerne ||
          r.tlp ||
          r.tags.length > 0 ||
          r.cve_associees.length > 0 ||
          r.ioc_associees.length > 0) && (
          <Card className="mb-5">
            <CardHead titre="Enrichissement" couleurPoint="var(--color-violet)" />
            <dl className="grid grid-cols-2 gap-x-8 gap-y-3 px-[18px] py-4 sm:grid-cols-3">
              {r.auteur && (
                <div>
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    Auteur
                  </dt>
                  <dd className="mt-0.5 text-[13px] font-medium">{r.auteur}</dd>
                </div>
              )}
              {r.niveau_confiance && (
                <div>
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    Niveau de confiance
                  </dt>
                  <dd className="mt-0.5 text-[13px] font-medium">{r.niveau_confiance_label}</dd>
                </div>
              )}
              {r.secteur_concerne && (
                <div>
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    Secteur concerné
                  </dt>
                  <dd className="mt-0.5 text-[13px] font-medium">{r.secteur_concerne}</dd>
                </div>
              )}
              {r.tlp && (
                <div>
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    TLP
                  </dt>
                  <dd className="mt-0.5 text-[13px] font-medium uppercase">{r.tlp}</dd>
                </div>
              )}
              {r.tags.length > 0 && (
                <div className="col-span-2 sm:col-span-3">
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    Tags
                  </dt>
                  <dd className="mt-1 flex flex-wrap gap-1.5">
                    {r.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-[5px] bg-surface-3 px-2 py-0.5 font-mono text-[11px] text-ink-soft"
                      >
                        {tag}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {r.cve_associees.length > 0 && (
                <div className="col-span-2 sm:col-span-3">
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    CVE associées
                  </dt>
                  <dd className="mt-0.5 font-mono text-[12.5px] text-ink-soft">{r.cve_associees.join(", ")}</dd>
                </div>
              )}
              {r.ioc_associees.length > 0 && (
                <div className="col-span-2 sm:col-span-3">
                  <dt className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    IOC associées
                  </dt>
                  <dd className="mt-0.5 font-mono text-[12.5px] text-ink-soft">{r.ioc_associees.join(", ")}</dd>
                </div>
              )}
            </dl>
          </Card>
        )}

        {d.cvss_axes.length > 0 && (
          <Card className="mb-5">
            <CardHead titre="Analyse CVSS" couleurPoint="var(--color-crit)" />
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 px-[18px] py-4 sm:grid-cols-4">
              {d.cvss_axes.map((a) => (
                <div key={a.code}>
                  <div className="font-mono text-[10px] font-semibold tracking-[0.09em] text-ink-faint uppercase">
                    {a.label}
                  </div>
                  <div className="mt-0.5 text-[13px] font-medium">{a.valeur}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Modal
          ouvert={modaleTraitement}
          titre={d.traitement ? "Modifier le traitement" : "Ajouter un traitement"}
          onFermer={() => setModaleTraitement(false)}
        >
          <Formulaire
            d={d}
            onEnregistre={() => {
              charger();
              setModaleTraitement(false);
            }}
          />
        </Modal>

        {d.traitement && d.traitement.historique.length > 0 && (
          <Card className="mt-5">
            <CardHead
              titre="Historique"
              couleurPoint="var(--color-accent)"
              action={
                <a
                  href={api.urlPdf(d.traitement.id)}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex items-center gap-1.5 hover:text-accent"
                >
                  <IconDownload className="size-3.5" />
                  PDF
                </a>
              }
            />
            <div className="flex flex-col">
              {d.traitement.historique.map((h, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 border-b border-border px-4 py-2.5 text-[12.5px] text-ink-soft last:border-b-0"
                >
                  <SevDot criticite="faible" />
                  <b className="font-semibold text-ink">{h.evenement}</b>
                  <span className="ml-auto font-mono text-[11.5px] text-ink-faint">
                    {dateLongue(h.horodatage)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

export default function PageDetail() {
  return (
    <Garde>
      <Contenu />
    </Garde>
  );
}
