"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, PageHead } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import {
  Button,
  Card,
  CardHead,
  Empty,
  ErreurChamp,
  Input,
  Kpi,
  Label,
  Modal,
  Select,
  Spinner,
} from "@/components/ui";
import { IconAlert, IconClock, IconDoc, IconDownload, IconPlus, IconServer, IconTrash, IconUp } from "@/components/icons";
import { ApiError, api } from "@/lib/api";
import { depuis } from "@/lib/format";
import type { Actif, HistoriqueActif, ProduitCatalogue, StatsActifs } from "@/lib/types";

/* ------------------------------------------------------------------ */
/* Ajout d'un actif : recherche « tape et trouve » dans le catalogue    */
/* ------------------------------------------------------------------ */
function ModaleAjout({
  ouvert,
  onFermer,
  onAjoute,
}: {
  ouvert: boolean;
  onFermer: () => void;
  onAjoute: () => void;
}) {
  const [type, setType] = useState<"technique" | "normatif">("technique");
  const [recherche, setRecherche] = useState("");
  const [resultats, setResultats] = useState<ProduitCatalogue[]>([]);
  const [choisi, setChoisi] = useState<ProduitCatalogue | null>(null);
  const [version, setVersion] = useState("");
  const [versionLibre, setVersionLibre] = useState("");
  const [referentiels, setReferentiels] = useState<string[]>([]);
  const [referentiel, setReferentiel] = useState("");
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (ouvert) api.referentiels().then(setReferentiels).catch(() => {});
  }, [ouvert]);

  // Recherche differee : le catalogue compte ~470 produits, inutile
  // d'interroger le serveur a chaque frappe.
  useEffect(() => {
    if (!ouvert || type !== "technique") return;
    const q = recherche.trim();
    if (q.length < 2) {
      setResultats([]);
      return;
    }
    const id = setTimeout(() => {
      api.catalogue(q).then(setResultats).catch(() => setResultats([]));
    }, 220);
    return () => clearTimeout(id);
  }, [recherche, ouvert, type]);

  function reinitialiser() {
    setRecherche("");
    setResultats([]);
    setChoisi(null);
    setVersion("");
    setVersionLibre("");
    setReferentiel("");
    setErreurs({});
  }

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setErreurs({});
    setEnvoi(true);
    try {
      const versionFinale = version === "__autre__" ? versionLibre : version;
      await api.creerActif(
        type === "technique"
          ? {
              type,
              categorie: choisi?.categorie ?? "",
              editeur: choisi?.editeur ?? "",
              produit: choisi?.produit ?? recherche.trim(),
              version: versionFinale,
            }
          : { type, referentiel }
      );
      reinitialiser();
      onAjoute();
      onFermer();
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.erreurs).length) setErreurs(err.erreurs);
      else setErreurs({ produit: err instanceof Error ? err.message : "Échec de l'ajout." });
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Modal ouvert={ouvert} titre="Ajouter un actif ou un référentiel" onFermer={onFermer}>
      <form onSubmit={soumettre}>
        <div className="mb-3.5 flex gap-[7px]">
          {(
            [
              ["technique", "Technique"],
              ["normatif", "Normatif"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => {
                setType(v);
                reinitialiser();
              }}
              className={`flex-1 rounded-lg border py-2 text-[12.5px] font-semibold transition-colors ${
                type === v
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {type === "technique" ? (
          <>
            <div className="mb-3.5">
              <Label>Rechercher un produit (ex : ubuntu, debian, pan-os…)</Label>
              <Input
                value={choisi ? `${choisi.produit} — ${choisi.editeur}` : recherche}
                onChange={(e) => {
                  setChoisi(null);
                  setVersion("");
                  setRecherche(e.target.value);
                }}
                placeholder="Tapez au moins 2 caractères…"
                autoComplete="off"
              />
              {!choisi && resultats.length > 0 && (
                <div className="mt-1.5 max-h-[230px] overflow-y-auto rounded-lg border border-border-strong bg-surface p-1 shadow-pop">
                  {resultats.map((p) => (
                    <button
                      key={`${p.editeur}/${p.produit}`}
                      type="button"
                      onClick={() => {
                        setChoisi(p);
                        setResultats([]);
                      }}
                      className="block w-full cursor-pointer rounded-md px-2.5 py-2 text-left text-[13px] text-ink-soft hover:bg-accent-soft hover:text-ink"
                    >
                      <b className="font-semibold text-ink">{p.produit}</b>
                      <span className="text-ink-faint">
                        {" "}
                        — {p.editeur} · {p.categorie}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              {!choisi && recherche.trim().length >= 2 && resultats.length === 0 && (
                <p className="mt-1.5 text-[11.5px] text-ink-faint">
                  Aucun produit du catalogue ne correspond — il sera ajouté tel que vous l&apos;avez saisi.
                </p>
              )}
              <ErreurChamp>{erreurs.produit}</ErreurChamp>
            </div>

            {choisi && choisi.versions.length > 0 && (
              <div className="mb-3.5">
                <Label>Version (optionnel)</Label>
                <Select value={version} onChange={(e) => setVersion(e.target.value)}>
                  <option value="">— Aucune —</option>
                  {choisi.versions.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                  <option value="__autre__">Autre (saisir)…</option>
                </Select>
                {version === "__autre__" && (
                  <Input
                    className="mt-2"
                    placeholder="Saisir la version"
                    value={versionLibre}
                    onChange={(e) => setVersionLibre(e.target.value)}
                  />
                )}
              </div>
            )}
          </>
        ) : (
          <div className="mb-3.5">
            <Label>Référentiel</Label>
            <Select value={referentiel} onChange={(e) => setReferentiel(e.target.value)}>
              <option value="">— Choisir —</option>
              {referentiels.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
            <ErreurChamp>{erreurs.referentiel}</ErreurChamp>
          </div>
        )}

        <Button type="submit" variante="primaire" disabled={envoi} className="mt-2">
          {envoi ? "Ajout…" : "Ajouter"}
        </Button>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
function ModaleVersion({
  actif,
  onFermer,
  onFait,
}: {
  actif: Actif | null;
  onFermer: () => void;
  onFait: () => void;
}) {
  const [version, setVersion] = useState("");
  const [versions, setVersions] = useState<string[]>([]);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!actif) return;
    setVersion(actif.version);
    api
      .catalogue(actif.produit)
      .then((r) => {
        const p = r.find((x) => x.produit.toLowerCase() === actif.produit.toLowerCase());
        setVersions(p?.versions ?? []);
      })
      .catch(() => setVersions([]));
  }, [actif]);

  if (!actif) return null;

  return (
    <Modal ouvert titre="Monter en version" onFermer={onFermer}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setEnvoi(true);
          try {
            await api.monterVersion(actif.id, version);
            onFait();
            onFermer();
          } finally {
            setEnvoi(false);
          }
        }}
      >
        <div className="mb-3.5">
          <Label>Actif</Label>
          <Input value={actif.libelle} disabled />
        </div>
        <div className="mb-3.5">
          <Label>Nouvelle version</Label>
          {versions.length ? (
            <Select value={version} onChange={(e) => setVersion(e.target.value)}>
              <option value="">— Aucune —</option>
              {versions.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </Select>
          ) : (
            <Input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="Saisir la version" />
          )}
        </div>
        <Button type="submit" variante="primaire" disabled={envoi}>
          {envoi ? "Enregistrement…" : "Enregistrer"}
        </Button>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
function ModaleRetrait({
  actif,
  onFermer,
  onFait,
}: {
  actif: Actif | null;
  onFermer: () => void;
  onFait: () => void;
}) {
  const [purger, setPurger] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => setPurger(false), [actif]);
  if (!actif) return null;

  return (
    <Modal ouvert titre="Retirer un actif" onFermer={onFermer}>
      <p className="mb-4 text-[13px] leading-relaxed text-ink-soft">
        Vous êtes sur le point de retirer <b className="text-ink">{actif.libelle}</b>. Choisissez ce
        qu&apos;il advient de son historique de traitement — ce choix est définitif.
      </p>
      <div className="mb-[18px] flex gap-2">
        {(
          [
            [false, "Conserver l'historique"],
            [true, "Purger l'historique"],
          ] as const
        ).map(([v, label]) => (
          <button
            key={String(v)}
            type="button"
            onClick={() => setPurger(v)}
            className={`flex-1 rounded-lg border py-[9px] text-[12.5px] font-semibold transition-colors ${
              purger === v
                ? "border-crit bg-crit-soft text-ink"
                : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <Button
        variante="danger"
        disabled={envoi}
        onClick={async () => {
          setEnvoi(true);
          try {
            await api.retirerActif(actif.id, purger);
            onFait();
            onFermer();
          } finally {
            setEnvoi(false);
          }
        }}
      >
        {envoi ? "Retrait…" : "Retirer"}
      </Button>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
function Contenu() {
  const params = useSearchParams();
  const typeInitial = params.get("type") ?? "";

  const [actifs, setActifs] = useState<Actif[] | null>(null);
  const [stats, setStats] = useState<StatsActifs | null>(null);
  const [historique, setHistorique] = useState<HistoriqueActif[]>([]);
  const [type, setType] = useState(typeInitial);
  const [recherche, setRecherche] = useState("");
  const [ajout, setAjout] = useState(false);
  const [versionDe, setVersionDe] = useState<Actif | null>(null);
  const [retraitDe, setRetraitDe] = useState<Actif | null>(null);

  const charger = useCallback(() => {
    api.actifs({ type: type || undefined }).then(setActifs).catch(() => setActifs([]));
    api.statsActifs().then(setStats).catch(() => {});
    api.historiqueActifs().then(setHistorique).catch(() => {});
  }, [type]);

  useEffect(charger, [charger]);

  const filtres = useMemo(() => {
    if (!actifs) return null;
    const q = recherche.trim().toLowerCase();
    return q ? actifs.filter((a) => a.libelle.toLowerCase().includes(q) || a.editeur.toLowerCase().includes(q)) : actifs;
  }, [actifs, recherche]);

  const TAG_HIST: Record<string, string> = {
    ajout: "bg-faib-soft text-faib",
    version: "bg-accent-soft text-accent",
    suppression_conserve: "bg-crit-soft text-crit",
    suppression_purge: "bg-crit-soft text-crit",
  };

  return (
    <AppShell compteurs={{ actifs: stats?.total }}>
      <PageHead
        titre="Gestion des actifs"
        sous="Votre inventaire pilote toute la veille : rien n'est remonté sur un actif non déclaré."
        actions={
          <Button variante="primaire" onClick={() => setAjout(true)}>
            <IconPlus className="size-3.5" />
            Ajouter un actif
          </Button>
        }
      />

      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi icone={<IconServer />} label="Total" valeur={stats?.total ?? "—"} detail="Actifs et référentiels" />
        <Kpi ton="accent" icone={<IconServer />} label="Technique" valeur={stats?.technique ?? "—"} detail="Produits exploités" />
        <Kpi ton="violet" icone={<IconDoc />} label="Normatif" valeur={stats?.normatif ?? "—"} detail="Référentiels suivis" />
        <Kpi ton="gold" icone={<IconAlert />} label="Non couverts" valeur={stats?.non_couverts ?? "—"} detail="Aucune source ne les suit" />
      </div>

      <div className="grid gap-[18px] xl:grid-cols-[1fr_300px]">
        <div>
          <div className="mb-3.5 flex flex-wrap items-center gap-2">
            <Input
              placeholder="Rechercher un actif…"
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              className="max-w-[300px] min-w-[190px] flex-1 text-[12.5px]"
            />
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
          </div>

          <Card>
            {filtres === null ? (
              <Spinner />
            ) : filtres.length ? (
              filtres.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center gap-3.5 border-b border-border px-[18px] py-3 text-[13px] last:border-b-0 hover:bg-surface-2"
                >
                  <span
                    className={`w-20 shrink-0 rounded-md px-2 py-[2.5px] text-center font-mono text-[9.5px] font-semibold tracking-[0.09em] uppercase ${
                      a.type === "technique" ? "bg-accent-soft text-accent" : "bg-violet-soft text-violet"
                    }`}
                  >
                    {a.type}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {a.libelle}
                    {a.version && (
                      <span className="ml-2 font-mono text-[11.5px] font-normal text-ink-faint">{a.version}</span>
                    )}
                  </span>
                  {!a.couvert && (
                    <span
                      className="shrink-0 cursor-help rounded-md border border-gold bg-gold-soft px-2.5 py-[2.5px] font-mono text-[9.5px] font-semibold tracking-[0.07em] text-gold uppercase"
                      title="Aucune source ne couvre cet actif pour l'instant — ce n'est pas une garantie d'absence de vulnérabilité, seulement une absence de collecte."
                    >
                      Non couvert
                    </span>
                  )}
                  <div className="flex shrink-0 gap-1.5">
                    {a.type === "technique" && (
                      <button
                        type="button"
                        onClick={() => setVersionDe(a)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-[5px] text-[11.5px] font-semibold text-ink-soft hover:border-border-strong hover:text-ink"
                      >
                        <IconUp className="size-3" />
                        Version
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setRetraitDe(a)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-[5px] text-[11.5px] font-semibold text-ink-soft hover:border-border-strong hover:text-ink"
                    >
                      <IconTrash className="size-3" />
                      Retirer
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <Empty
                icone={<IconServer />}
                action={
                  !recherche && !type ? (
                    <Button variante="primaire" onClick={() => setAjout(true)}>
                      <IconPlus className="size-3.5" />
                      Déclarer mon premier actif
                    </Button>
                  ) : undefined
                }
              >
                {recherche || type ? (
                  "Aucun actif ne correspond à ces critères."
                ) : (
                  <>
                    Votre inventaire est vide.
                    <br />
                    Commencez par déclarer un produit que vous exploitez — un pare-feu, un OS, une
                    base de données.
                  </>
                )}
              </Empty>
            )}
          </Card>
        </div>

        <aside className="flex flex-col gap-3.5">
          <div className="rounded-2xl border border-border bg-surface px-[18px] py-4 text-[12.5px] leading-relaxed text-ink-soft">
            <b className="mb-1.5 block text-[13.5px] text-ink">Comment bien déclarer</b>
            Un actif trop générique ne produit aucune veille exploitable.
            <ul className="mt-2 list-disc pl-4">
              <li className="mb-1.5">
                Descendez au niveau <b className="text-ink">produit</b> : « Palo Alto PAN-OS », pas
                « Pare-feu ».
              </li>
              <li className="mb-1.5">
                Renseignez la <b className="text-ink">version</b> quand vous la connaissez.
              </li>
              <li>
                Un logiciel se déclare en <b className="text-ink">technique</b>, jamais en normatif :
                le normatif, ce sont les référentiels (ISO, RGPD).
              </li>
            </ul>
          </div>

          <Card>
            <CardHead titre="Historique" couleurPoint="var(--color-ink-faint)" />
            <div className="flex flex-1 flex-col">
              {historique.length ? (
                historique.slice(0, 12).map((h) => (
                  <div key={h.id} className="border-b border-border px-4 py-[11px] text-[12.5px] last:border-b-0">
                    <div className="mb-1.5 font-mono text-[11px] text-ink-faint">
                      Il y a {depuis(h.horodatage)}
                    </div>
                    <div>
                      <span
                        className={`mr-[7px] inline-flex rounded-md px-[7px] py-0.5 font-mono text-[9.5px] font-semibold tracking-[0.07em] uppercase ${
                          TAG_HIST[h.evenement] ?? "bg-surface-3 text-ink-faint"
                        }`}
                      >
                        {h.evenement_label}
                      </span>
                      {h.actif_repr}
                    </div>
                    {h.detail && <div className="mt-1 text-[11.5px] text-ink-soft">{h.detail}</div>}
                  </div>
                ))
              ) : (
                <Empty icone={<IconClock />}>Aucune modification pour le moment.</Empty>
              )}
            </div>
          </Card>
        </aside>
      </div>

      <ModaleAjout ouvert={ajout} onFermer={() => setAjout(false)} onAjoute={charger} />
      <ModaleVersion actif={versionDe} onFermer={() => setVersionDe(null)} onFait={charger} />
      <ModaleRetrait actif={retraitDe} onFermer={() => setRetraitDe(null)} onFait={charger} />
    </AppShell>
  );
}

export default function PageActifs() {
  return (
    <Garde>
      <Suspense fallback={<Spinner />}>
        <Contenu />
      </Suspense>
    </Garde>
  );
}
