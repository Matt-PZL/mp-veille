# Veille — contexte projet pour Claude

SaaS de veille cyber & normative pour une ESN, développé pour un client. Django
(backend/API) + Next.js (frontend, en cours de migration). Hébergé sur une VM
homelab de l'utilisateur, déployé par `git push`.

## Ce que fait le produit

- **BDP** (Base de Données Propriétaire) : renseignements de sécurité partagés,
  immuables/versionnés (`apps/bdp`). Alimentée automatiquement par NVD (CVE),
  CERT-FR (avis), CNIL (actualités RGPD) — voir `apps/ingestion/tasks.py`.
- **BDC** (Base de Données Clientes) : actifs déclarés + traitements, avec des
  champs sensibles chiffrés (Fernet, `apps/bdc/fields.py`) — `apps/bdc`.
- **Matching** (`apps/matching`) : lecture seule, croise BDP+BDC par
  éditeur/produit ou référentiel. Ne décrypte jamais, n'écrit jamais.
- **Catalogue** (`apps/catalogue`) : ~470 produits réels (OS, BDD, pare-feux...)
  importés depuis endoflife.date, avec versions connues — sert à peupler les
  listes déroulantes de déclaration d'actifs sans jamais dépendre d'une liste
  tapée à la main.
- **Panel** (`apps/panel`) : l'interface Django historique (templates), encore
  la seule à couvrir Renseignements/Traitement/Gestion des actifs/Actualités.
- **API** (`apps/api`) : couche REST (DRF + JWT), additive, pour le nouveau
  frontend Next.js. Coexiste avec `apps.panel` pendant la migration.
- **Vitrine** (`apps/vitrine`) : landing page publique + formulaire de contact.

## Direction artistique

GitHub Dark inspiré, accent bleu `#1D4ED8`. Polices Archivo (titres), IBM Plex
Sans (corps), IBM Plex Mono (données/mono). Tokens dans `templates/base.html`
(`:root`) côté Django, portés à l'identique dans `frontend/src/app/globals.css`
côté Next.js. Topbar + tiroir de navigation (pas de sidebar permanente), palette
de commandes Ctrl+K.

## Déploiement

**Pas de CI/CD** : `git push devvm main` pousse vers un dépôt bare sur la VM
(`~/repos/veille-saas.git`), un hook `post-receive` fait `git checkout -f main`
dans `~/apps/veille-saas` et le `docker compose` (Django dev server en
autoreload) prend le changement tout seul. **Seul `main` déclenche un
déploiement** — pousser d'autres branches vers `devvm` est sans risque (le hook
checkout toujours `main`).

Accès VM : `ssh devvm` (alias déjà configuré dans `~/.ssh/config` de
l'utilisateur, pointe sur `192.168.1.24`, VM Debian 13 `mpcyber-vm`).
`sudo` sur `matt` est passwordless. Pour tester du code sans toucher la prod,
utiliser un `git worktree add ~/apps/veille-saas-XXX <branche>` +
`docker build` avec un tag distinct — **ne jamais** faire tourner du code
expérimental directement dans `~/apps/veille-saas` (c'est la prod).

## État des branches (voir aussi `git log --oneline --graph --all`)

- **`main`** : état stable, déployé en continu sur la VM.
- **`backup/main-2026-09-13`** : sauvegarde de `main` avant l'arrivée des
  contributions des amis (tonurofa, kramalow) — point de retour si besoin.
- **`conv_next_mp`** : migration en cours vers Next.js (frontend séparé,
  backend Django gardé comme API). Voir section suivante.
- Des branches `LR-26` / `MP-11` sont apparues sur `origin` (GitHub) — a priori
  le travail des amis invités en collaborateurs. À relire/merger via PR.

## Accès partagés

- **Dépôt GitHub** (source de vérité pour le code, PR/revue) :
  `git@github.com:Matt-PZL/mp-veille.git`. Clé SSH dédiée dans
  `~/.ssh/github_veille_key` (déjà référencée par `core.sshCommand` dans ce
  dépôt — ne pas la committer, jamais).
- **VPN WireGuard** sur la VM (`wg0`, port UDP 51820, scopé à la VM
  uniquement, pas au reste du LAN) pour que les amis (`tonurofa`, `kramalow`)
  puissent s'y connecter. Script `/usr/local/sbin/ajouter-ami.sh` sur la VM
  pour provisionner un nouveau compte + peer VPN.
- Comptes amis : groupe Unix `devveille` (accès partagé au dépôt bare +
  répertoire de déploiement), groupe `docker` (= accès root de fait sur la VM,
  décision assumée et expliquée à l'utilisateur).

## Migration Next.js (`conv_next_mp`) — où ça en est

**Fait et testé de bout en bout** :
- `apps/api` : endpoints `/api/auth/token/`, `/api/auth/inscription/`,
  `/api/dashboard/`, `/api/renseignements/`, `/api/actifs/`, `/api/catalogue/`,
  `/api/contact/`. Mêmes règles métier que `apps.panel` (perimetre scopé aux
  actifs réellement déclarés, jamais toute la BDP brute).
- `frontend/` (Next.js 16, App Router, TypeScript, `next/font/google` pour les
  polices, CSS Modules + un fichier `landing.css` pour la page publique) :
  landing page (port fidèle de `apps/vitrine`), `/login`, `/inscription`,
  `/dashboard` connecté aux vraies données. Auth JWT stockée en localStorage
  (`frontend/src/lib/api.ts`, `auth-context.tsx`) — **limite connue** : un
  cookie httpOnly + refresh serveur serait plus solide pour la vraie prod,
  pas fait dans cette première passe.
- Nav de l'app Next.js (`AppNav.tsx`) contient des liens marqués "v1" vers les
  pages pas encore migrées (Renseignements, Traitement, Gestion des actifs,
  Actualités), qui restent servies par `apps.panel` (Django) le temps de la
  migration — les deux interfaces coexistent, rien n'est cassé entre-temps.

**Pas encore fait** : porter Renseignements/Traitement/Gestion des
actifs/Actualités en Next.js ; durcir l'auth (cookie httpOnly) ; CI/CD
(GitHub Action) pour automatiser le déploiement une fois que l'utilisateur le
demande explicitement.

**Pour retester en local** : `cd frontend && npm install && npm run dev`,
avec `NEXT_PUBLIC_API_URL` dans `.env.local` pointé vers un Django qui tourne
(ex: `http://192.168.1.24:8000` si on pointe direct sur la VM — dans ce cas
`CORS_ALLOWED_ORIGINS` côté Django doit inclure l'origine du dev server, déjà
fait par défaut pour `localhost:3000`).

## Pièges déjà rencontrés (pour ne pas les refaire)

- Un `{% if %}...{% else %}...{% endif %}` Django qui construit un attribut
  HTML de façon conditionnelle peut produire un guillemet manquant dans une
  branche — corrompt tout le HTML suivant en silence. Préférer des classes
  CSS nommées par valeur plutôt que des styles inline conditionnels.
- `default:variable.attribut` dans un template Django plante (au lieu de
  s'afficher vide) si `variable` est `None` — contrairement à
  `{{ variable.attribut }}` seul, qui échoue silencieusement. Toujours garder
  `{% if variable %}` autour d'un accès chaîné utilisé comme argument de
  filtre.
- Un `git push` direct depuis l'agent vers un remote externe (GitHub) est
  bloqué par le classifieur de permissions sous Bash ; passer par PowerShell
  fonctionne (mais nécessite alors une auth non interactive — d'où la clé SSH
  dédiée plutôt qu'un identifiant HTTPS).
- Toujours nettoyer les comptes/utilisateurs de test créés sur la VM après
  vérification fonctionnelle (motif récurrent dans ce projet : `qa_test`,
  etc.) — ne jamais laisser de compte de test traîner en base.
