# Contexte Lucas — décisions et notes propres à sa partie

Fichier complémentaire à `CLAUDE.md` (importé automatiquement dedans via
`@CLAUDE.lucas.md`), pour ne pas mélanger deux façons de documenter le
projet. **Lucas (ou toute autre personne qui reprend son travail) : ajoute
ici ce qui n'est vrai que pour cette partie du code** — tes choix
d'architecture, tes pièges rencontrés, ce qu'un futur Claude devrait savoir
avant de toucher à tes fichiers. Pas besoin de repasser par Matt pour éditer
ce fichier.

## Ce qu'on sait déjà de tes choix (déduit du code, à confirmer/corriger)

- **django-ninja plutôt que DRF** pour `apps/api/` — plus léger, typé par
  Pydantic. Si le choix a une raison précise (perf, préférence, contrainte),
  vaut le coup de la noter ici pour que personne ne le remette en question
  sans savoir pourquoi.
- **Auth par cookie de session httpOnly** plutôt que JWT en localStorage —
  plus sûr par défaut (le token n'est jamais accessible en JS), au prix d'un
  aller-retour `GET /api/auth/csrf` avant toute écriture. Si tu as buté sur
  un détail CSRF/cookie particulier pendant l'implémentation, c'est le genre
  de chose qui vaut d'être notée ici plutôt que redécouverte.
- **Remplacement complet plutôt que coexistence** : contrairement à une
  première tentative sur `main` qui gardait les templates Django en
  fallback, ta version supprime `apps.panel`/`apps.vitrine` entièrement —
  Next.js est la seule UI. Décision du client actée, mais si tu as des
  réserves ou des compromis que ça t'a imposés, c'est le bon endroit pour
  les documenter.
- **Tailwind v4** (config CSS-first, pas de `tailwind.config.*`) plutôt que
  du CSS Modules — cohérent avec le reste de tes choix (aller vite, moins de
  fichiers de config).

## Zone libre — tes notes

<!-- Ajoute ici : pièges rencontrés, décisions non évidentes en relisant le
code seul, ce qui reste à faire de ton côté, tout ce qui te ferait gagner du
temps si quelqu'un d'autre (humain ou Claude) reprenait cette partie demain. -->
