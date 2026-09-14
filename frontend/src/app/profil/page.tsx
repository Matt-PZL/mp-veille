"use client";

import { useEffect, useState } from "react";
import { AppShell, PageHead } from "@/components/AppShell";
import { Garde } from "@/components/Garde";
import { Button, Card, CardHead, Label, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useUi, type Accent, type Nav } from "@/lib/ui-context";
import type { Preferences } from "@/lib/types";

/** Aperçu schématique d'une disposition, pour choisir sans avoir à essayer. */
function Apercu({ nav }: { nav: Nav }) {
  const bloc = "rounded-[2px] bg-current";
  if (nav === "horizontale") {
    return (
      <div className="flex h-12 w-full flex-col gap-1 rounded-md border border-current/25 p-1.5">
        <div className={`h-2 w-full ${bloc} opacity-70`} />
        <div className="flex flex-1 gap-1">
          <div className={`w-1/4 ${bloc} opacity-25`} />
          <div className={`flex-1 ${bloc} opacity-15`} />
        </div>
      </div>
    );
  }
  // Tiroir : superpose au contenu, pas une colonne qui pousse la page.
  return (
    <div className="relative flex h-12 w-full flex-col gap-1 overflow-hidden rounded-md border border-current/25 p-1.5">
      <div className={`h-2 w-full ${bloc} opacity-40`} />
      <div className="flex flex-1 gap-1">
        <div className={`w-1/4 ${bloc} opacity-25`} />
        <div className={`flex-1 ${bloc} opacity-15`} />
      </div>
      <div className="absolute inset-y-0 left-0 w-1/3 border-r border-current/40 bg-current opacity-80" />
    </div>
  );
}

function Apparence() {
  const { mode, accent, nav, basculerMode, choisirAccent, choisirNav } = useUi();

  const option = (actif: boolean) =>
    `flex-1 rounded-xl border px-3 py-3 text-left transition-colors ${
      actif
        ? "border-accent bg-accent-soft text-accent"
        : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
    }`;

  return (
    <Card>
      <CardHead titre="Apparence" couleurPoint="var(--color-violet)" />
      <div className="px-[18px] py-4">
        <Label>Disposition de la navigation</Label>
        <div className="mb-1.5 flex gap-2.5">
          {(
            [
              ["horizontale", "Horizontale", "Onglets en haut, sur une seule ligne."],
              ["verticale", "Verticale", "Tiroir latéral qui s'ouvre au clic, comme au début du projet."],
            ] as const
          ).map(([v, titre, detail]) => (
            <button key={v} type="button" onClick={() => choisirNav(v)} className={option(nav === v)}>
              <Apercu nav={v} />
              <div className="mt-2.5 text-[13px] font-semibold">{titre}</div>
              <div className="mt-0.5 text-[11.5px] leading-snug text-ink-faint">{detail}</div>
            </button>
          ))}
        </div>
        <p className="mb-5 text-[11.5px] leading-relaxed text-ink-faint">
          En disposition verticale, le bouton à gauche de la barre ouvre le menu par-dessus la page.
          Il se referme dès qu&apos;on choisit une section, au clic à côté, ou avec Échap.
        </p>

        <Label>Thème</Label>
        <div className="mb-5 flex gap-2.5">
          {(
            [
              ["dark", "Sombre"],
              ["light", "Clair"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => {
                if (mode !== v) basculerMode();
              }}
              className={`flex-1 rounded-lg border py-2.5 text-[12.5px] font-semibold transition-colors ${
                mode === v
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <Label>Couleur d&apos;accent</Label>
        <div className="flex gap-2.5">
          {(
            [
              ["bleu", "#3B7BFF", "Bleu"],
              ["vert", "#3DBB6E", "Vert"],
              ["violet", "#A371F7", "Violet"],
            ] as const
          ).map(([v, couleur, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => choisirAccent(v as Accent)}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg border py-2.5 text-[12.5px] font-semibold transition-colors ${
                accent === v
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border bg-surface-2 text-ink-soft hover:border-border-strong hover:text-ink"
              }`}
            >
              <span className="size-2.5 rounded-full" style={{ background: couleur }} />
              {label}
            </button>
          ))}
        </div>

        <p className="mt-5 text-[11.5px] leading-relaxed text-ink-faint">
          Ces réglages sont propres à ce navigateur : ils ne suivent pas votre compte d&apos;un poste
          à l&apos;autre.
        </p>
      </div>
    </Card>
  );
}

function Contenu() {
  const { utilisateur } = useAuth();
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [enregistre, setEnregistre] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    api.preferences().then(setPrefs).catch(() => {});
  }, []);

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    if (!prefs) return;
    setEnvoi(true);
    setEnregistre(false);
    try {
      setPrefs(await api.enregistrerPreferences(prefs));
      setEnregistre(true);
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <AppShell>
      <PageHead titre="Profil" sous="Compte, notifications et apparence du panel." />

      <div className="grid gap-3.5 lg:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-5">
          <Card>
            <CardHead titre="Compte et notifications" couleurPoint="var(--color-accent)" />
            <div className="px-[18px] py-4">
              <div className="mb-[22px] flex items-center gap-3.5 rounded-xl border border-border bg-surface-2 px-4 py-3.5">
                <span className="flex size-[38px] shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono text-sm font-bold text-accent uppercase">
                  {utilisateur?.username.slice(0, 2)}
                </span>
                <span className="min-w-0">
                  <div className="font-mono text-[10px] font-semibold tracking-[0.11em] text-ink-faint uppercase">
                    Compte
                  </div>
                  <div className="truncate text-sm font-semibold">
                    {utilisateur?.email || utilisateur?.username}
                  </div>
                </span>
              </div>

              {!prefs ? (
                <Spinner />
              ) : (
                <form onSubmit={soumettre}>
                  <div className="mb-4">
                    <Label>Seuil de criticité des notifications</Label>
                    <Select
                      value={prefs.seuil_criticite}
                      onChange={(e) => setPrefs({ ...prefs, seuil_criticite: e.target.value })}
                    >
                      <option value="critique">Critique uniquement</option>
                      <option value="elevee">Élevée et plus</option>
                      <option value="moyenne">Moyenne et plus</option>
                    </Select>
                  </div>
                  <div className="mb-4">
                    <Label>Fréquence des alertes</Label>
                    <Select
                      value={prefs.frequence}
                      onChange={(e) => setPrefs({ ...prefs, frequence: e.target.value })}
                    >
                      <option value="immediat">Immédiat</option>
                      <option value="quotidien">Quotidien</option>
                      <option value="hebdo">Hebdomadaire</option>
                    </Select>
                  </div>
                  <div className="mt-5 flex items-center gap-3">
                    <Button type="submit" variante="primaire" disabled={envoi}>
                      {envoi ? "Enregistrement…" : "Enregistrer"}
                    </Button>
                    {enregistre && (
                      <span className="text-[12.5px] font-medium text-faib">Enregistré.</span>
                    )}
                  </div>
                  <p className="mt-4 text-[11.5px] leading-relaxed text-ink-faint">
                    Ces préférences sont enregistrées, mais l&apos;envoi des alertes n&apos;est pas
                    encore branché — aucune notification ne part pour l&apos;instant.
                  </p>
                </form>
              )}
            </div>
          </Card>
        </div>

        <div className="xl:col-span-7">
          <Apparence />
        </div>
      </div>
    </AppShell>
  );
}

export default function PageProfil() {
  return (
    <Garde>
      <Contenu />
    </Garde>
  );
}
