# Architecture
Les choix suivants sont considérés comme validés :
 
- BDP indépendante de BDC
- Matching en lecture seule
- Django comme backend
- Next.js comme frontend
- Celery + Redis pour les traitements asynchrones
 
Ne pas remettre en question ces choix sauf demande explicite.

## Vue générale

Client

↓

Frontend SaaS

↓

API Backend

↓

Services métier

↓

Base de données

↓

Collecteurs de renseignement

## Domaines principaux

### Assets

Gestion des actifs :

- Logiciels
- OS
- Technologies
- Produits
- Conformité

### Intelligence

Collecte :

- CVE
- News
- Advisory
- Patchs

### Correlation

Association entre :

Actifs ↔ Renseignements

### Workflow

Cycle de traitement :

- Nouveau
- En cours
- Analyse
- Applicable
- Non applicable
- Résolu
- Clos

## Objectifs

- Architecture modulaire
- Forte traçabilité
- Scalabilité horizontale