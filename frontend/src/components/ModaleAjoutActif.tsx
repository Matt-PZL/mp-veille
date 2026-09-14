"use client";

/**
 * Ajout d'un actif ou d'un referentiel — recherche « tape et trouve » dans
 * le catalogue. Extrait de la page /actifs pour etre reutilise tel quel
 * partout ou on veut ajouter un actif sans quitter la page (ex :
 * /renseignements, colonne Actifs).
 */

import { useEffect, useState } from "react";
import { Button, ErreurChamp, Input, Label, Modal, Select } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { ProduitCatalogue } from "@/lib/types";

export function ModaleAjoutActif({
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
