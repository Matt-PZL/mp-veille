# Décisions d'architecture

## Décisions validées

### D001

La plateforme est multi-tenant.

Statut : VALIDÉ

---

### D002

Les renseignements sont stockés localement après collecte.

Statut : VALIDÉ

---

### D003

Les workflows utilisateurs sont historisés.

Statut : VALIDÉ

---

### D004

L'animation du site vitrine s'appuie sur GSAP (`gsap` + `@gsap/react`).

Le hero d'accueil enchaîne une séquence continue — déplacement du réticule,
verrouillage, lecture, maintien, relâchement — qu'une timeline GSAP exprime
directement et met en pause d'un seul appel (survol, hors écran, onglet masqué).
`MotionPathPlugin` fournit la trajectoire courbe du réticule, et `gsap.ticker`
sert de boucle d'animation unique, partagée avec le canvas d'ambiance.

Licence : GSAP est gratuit, plugins inclus, usage commercial couvert, depuis le
30 avril 2025 (Standard « No Charge » GSAP License).

Périmètre : le panel applicatif sous `/app` n'en dépend pas.

Statut : VALIDÉ

---

## Convention

Toute nouvelle décision importante doit être ajoutée ici.