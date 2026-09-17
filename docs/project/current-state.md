# Etat Actuel

## Phase

Pré-production

## Architecture

Monorepo :
- Next.js
- Django Ninja
- PostgreSQL

## Fonctionnalités terminées

- Matching V2
- Ingestion
- Export PDF
- Auth
- Dashboard
- Traitements
- Collecteurs
- Site vitrine : hero de la page d'accueil (`/`)
- Panel applicatif isolé sous `/app` (découplé du site vitrine)

## Priorité actuelle

Industrialisation

## Blocages

Aucun

## Risques

- Absence de CI
- Peu de tests hors matching
- Sauvegarde chiffrement non finalisée
- Hero vitrine : la fiche « fuite de données » annonce une fonction non encore
  modélisée en BDP (`NATURE_CHOICES` n'a pas de nature `fuite`). À brancher sur
  le modèle ou à retirer avant mise en ligne publique.
- Hero vitrine : logos de marques tierces affichés à titre nominatif, à faire
  valider juridiquement avant mise en ligne publique.
- Dev Docker/Windows : le conteneur `frontend` (Next.js 16 / Turbopack) ne
  recompile pas automatiquement sur bind-mount — `WATCHPACK_POLLING` (dans
  `docker-compose.yml`) est une option Webpack, sans effet sur Turbopack. Un
  `docker restart` du conteneur `frontend` est nécessaire pour voir une
  modification prise en compte tant que ce n'est pas corrigé.

## Prochain objectif

Mise en place CI GitHub Actions
``