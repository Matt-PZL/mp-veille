# Veille — contexte projet pour Claude (branche `next-migration`)

Réécriture complète du frontend en Next.js. **Pas encore mergée dans `main`,
pas déployée en production** — testée uniquement via des serveurs de dev sur
la VM. Ce fichier est lu automatiquement en début de session ; le tenir à
jour évite de refaire des heures d'investigation déjà faites.

@CLAUDE.lucas.md

## D'où vient cette branche

Un collaborateur (Lucas) a poussé sa propre migration Next.js sur GitHub
(`NEXT-JS`), en remplacement complet plutôt qu'en coexistence — à l'opposé
d'une première tentative (`conv_next_mp`, sur `main`, incrémentale, DRF+JWT,
gardait les templates Django en fallback). Après comparaison, décision du
client : repartir de la base de Lucas. `next-migration` a été créée depuis
`github/NEXT-JS` puis détachée (aucun tracking vers sa branche — c'est
maintenant une ligne de dev à nous, pas la sienne).

**Backend** (`apps/bdp`, `apps/bdc`, `apps/matching`, `apps/catalogue`,
`apps/ingestion`) : identique à `main`, voir son `CLAUDE.md` pour
l'architecture, l'ingestion, la perf (index trigram) et les pièges déjà
rencontrés — pas reproduit ici. Seule différence backend : **API en
django-ninja** (`apps/api/`, `apps/api/routers/*.py`, `apps/api/api.py`) et
non DRF, **auth par cookie de session httpOnly** (pas de JWT en
localStorage) — voir `apps/api/routers/auth.py`.

## Frontend

Next.js 16 (App Router, Turbopack), TypeScript, Tailwind CSS v4 (config
CSS-first dans `frontend/src/app/globals.css`, pas de `tailwind.config.*`).
Design system : `--color-*` en `:root` (sombre par défaut) +
`:root[data-theme="light"]`, exposés via `@theme inline`. Composants
partagés dans `frontend/src/components/ui.tsx` (`Modal`, `Kpi`, `StatusPill`,
`Toggle`...).

Routes couvertes : `/`, `/connexion`, `/renseignements` (+ `[id]`),
`/traitement`, `/actifs`, `/actualites`, `/profil`. **Pas de landing page
publique** (`/` va direct sur la garde d'authentification) — contrairement à
`apps.vitrine` sur `main`, à porter si le client la veut un jour ici.

### Proxy API same-origin — ne jamais y toucher sans comprendre pourquoi

`next.config.ts` relaie `/api/*` côté serveur Next.js vers Django
(`API_INTERNAL_URL`, variable d'env **jamais exposée au navigateur** —
`frontend/src/lib/api.ts` a `BASE = ""`, toujours same-origin). C'est
volontaire et corrige un vrai bug : les navigateurs récents (Chrome/Edge)
bloquent en silence (`ERR_BLOCKED_BY_CLIENT`, sans trace réseau visible) tout
`fetch()` JS vers une IP privée (Private Network Access) — le front et l'API
tournant tous deux sur le LAN, un appel direct au port Django plantait la
vérification de session en boucle infinie sans erreur exploitable.
`CORS_ALLOW_PRIVATE_NETWORK=True` côté Django existe aussi mais **ne suffit
pas seul** (Chrome peut aussi bloquer via une permission navigateur plutôt
que l'en-tête CORS) — le proxy same-origin est le fix qui marche dans tous
les cas, à garder même si la cause semble un jour obsolète.

### `Modal` (`ui.tsx`) utilise un portail React — ne pas revenir en arrière

`createPortal(..., document.body)`. Sans lui, une modale ouverte depuis un
ancêtre en `position: sticky` (ex. la colonne Actifs dans sa sidebar
collante) hérite du contexte d'empilement de cet ancêtre et se peint
**derrière** le contenu principal au lieu de flotter au-dessus — bug réel
rencontré et corrigé, invisible en dev tant qu'on ne teste pas depuis un
composant imbriqué dans un élément positionné.

### Nav — une seule source de vérité pour les compteurs

`AppShell` récupère les pastilles de nav (`Renseignements 13`, `Actifs 2`...)
**une seule fois, lui-même**, via `GET /dashboard/compteurs-nav` — jamais
via une prop passée par chaque page. Avant ce fix, chaque page fournissait
son propre sous-ensemble de compteurs, faisant apparaître/disparaître les
badges selon la page ouverte. Préférence utilisateur : réglage Profil >
"Compteurs dans la navigation" (toujours affichés ou jamais), champ
`afficher_compteurs_nav` sur `PreferenceNotification`.

Piège symétrique déjà rencontré : `GET /traitements/compteurs` (stats de la
page Traitement elle-même) et `GET /dashboard/compteurs-nav` (badge de nav)
utilisent **volontairement** des périmètres différents — le premier compte
TOUS les `Traitement` (y compris ceux dont l'actif a été supprimé, c'est la
preuve d'audit), le second est scopé au périmètre matching actuel. Ne pas
les unifier, chaque page doit juste rester cohérente avec elle-même.

## Historique des actions (item récent)

`ActionHistorique` (`apps/bdc/models.py`) : journal unifié Actifs +
Traitements, alimenté par `apps/api/journal.py::consigner()` en plus (jamais
à la place) des journaux spécifiques existants (`HistoriqueActif`,
`HistoriqueTraitement`). Panneau front sur `/renseignements` (colonne de
droite, masqué sous `xl` faute de place). Pas de catégorie "Renseignements"
dans ce journal : aucune création/suppression de `Renseignement` n'existe
côté API (uniquement ingéré en tâche de fond) — décision assumée, pas un
oubli.

## Tester en local sur la VM

```
cd ~/dev/veille-saas/frontend && npm run dev -- -p 3001
```
`.env.local` (non commité) : `API_INTERNAL_URL=http://localhost:8011` (ou le
port du backend django-ninja de test en cours). Toujours arrêter le process
une fois fini — motif récurrent : des serveurs de dev oubliés tournent des
heures sur la VM.

## Champs d'enrichissement Renseignement — divergence avec `main`

`auteur`, `niveau_confiance`, `tags`, `secteur_concerne`, `tlp`,
`cve_associees`, `ioc_associees` existent ici (migration `bdp/0004`) **et
aussi sur `main`**, ajoutés indépendamment dans les deux branches avec le
même nom de migration mais un contenu différent (`main` a en plus la
contrainte unique et les index trigram que cette branche n'a pas). À
réconcilier manuellement au merge — voir le `CLAUDE.md` de `main` pour le
détail.
