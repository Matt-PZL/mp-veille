# Veille — contexte projet pour Claude (branche `main`)

SaaS de veille cyber & normative pour une ESN, développé pour un client, hébergé
sur une VM homelab (`ssh devvm`, Debian 13, `192.168.1.24`), déployé par
`git push` (pas de CI/CD). Ce fichier est lu automatiquement en début de
session — le tenir à jour évite de refaire des heures d'investigation déjà
faites. Mets-le à jour toi-même après un changement structurant, plutôt que
d'attendre qu'on te le demande.

## ⚠️ Deux branches actives, pas encore fusionnées

- **`main`** (ce fichier) : backend Django + **frontend historique en
  templates Django** (`apps/panel`, `apps/vitrine`). C'est ce qui tourne
  réellement en production (`~/apps/veille-saas`, conteneurs
  `veille-saas-{web,worker,beat,db,redis}-1`).
- **`next-migration`** : réécriture complète du frontend en Next.js, partie
  d'une base récupérée d'un collaborateur (Lucas, branche GitHub `NEXT-JS`) —
  django-ninja + auth par cookie de session au lieu de DRF+JWT, Tailwind v4.
  **Pas encore mergée dans `main`, pas déployée en prod** — testée uniquement
  via des serveurs de dev sur la VM (`~/dev/veille-saas`, ports 3000/3001).
  Son propre `CLAUDE.md` + `CLAUDE.lucas.md` (contexte que Lucas peut
  enrichir) vivent sur cette branche.
- **Piège de fusion à anticiper** : les deux branches ont chacune ajouté les
  mêmes 7 champs d'enrichissement à `Renseignement` (`auteur`,
  `niveau_confiance`, `tags`, `secteur_concerne`, `tlp`, `cve_associees`,
  `ioc_associees`) dans une migration `bdp/0004` **de même nom mais de
  contenu différent** sur chaque branche. `main` a ensuite ajouté 0005
  (contrainte unique) et 0006 (index trigram) que `next-migration` n'a pas.
  **À réconcilier manuellement au moment du merge**, pas un simple
  fast-forward.
- Backup de sécurité : branche `backup/main-2026-09-13` (point de retour
  avant les contributions d'amis).

## Architecture (partagée par les deux branches — backend inchangé)

- **BDP** (`apps/bdp`) : renseignements de sécurité, immuables/versionnés
  (jamais écrasés — nouvelle ligne liée via `parent` si le contenu change).
  **Volontairement indépendante de la BDC** : l'ingestion ne doit jamais
  filtrer par ce qu'un client a déclaré (principe clarifié en cours de
  projet — voir section Ingestion).
- **BDC** (`apps/bdc`) : actifs déclarés + traitements par client, champs
  sensibles chiffrés (Fernet, `apps/bdc/fields.py`).
- **Matching** (`apps/matching/services.py::calculer_matching()`) : lecture
  seule, croise BDP+BDC par éditeur/produit (technique) ou référentiel
  (normatif), avec paliers de confiance. Jamais decrypte, jamais n'écrit.
  Appelé à chaque requête API concernée (non caché) — **d'où l'importance
  des index trigram**, voir plus bas.
- **Catalogue** (`apps/catalogue`) : ~470 produits (endoflife.date) pour les
  listes déroulantes de déclaration d'actif.
- **Ingestion** (`apps/ingestion/tasks.py`) : voir section dédiée.

## Ingestion — BDP proactive, 6 sources réelles

Toutes les sources écrivent via `normaliser_et_ecrire_bdp()` (seul point
d'écriture BDP, dédoublonnage par `source + reference_externe`, contrainte
unique DB sur `+ decouvert_le`). `cycle_ingestion()` orchestre tout, planifié
toutes les 12h (`CELERY_BEAT_SCHEDULE`). Déclenchement manuel :
`python manage.py ingerer [--source nvd|kev|cert_fr_avis|cert_fr_alertes|
cnil|debian|ubuntu_usn|github_advisories|catalogue]`.

| Source | Type | Notes |
|---|---|---|
| NVD | technique | Proactif par fenêtre de dates (`pubStartDate`/`pubEndDate`), **plus aucune dépendance aux actifs déclarés** — avant, ne cherchait que par mot-clé par `ActifClient`, ce qui ratait tout produit non déclaré (ex : OpenSSH). `NVD_API_KEY` (env, gratuite) accélère 5→50 req/30s. |
| CERT-FR avis + alertes | technique | `_collecter_cert_fr()` générique, deux flux JSON de même forme. |
| Debian Security Tracker | technique | CVE encore `status=open` par paquet. Pas de date dans la source → réutilise `decouvert_le` existant si déjà connu. Clé composite `CVE::paquet` (une CVE peut toucher plusieurs paquets). |
| Ubuntu USN | technique | Pagination `limit`/`offset`, **max `limit=20`** (422 au-delà). |
| GitHub Advisories | technique | Écosystème open-source (pip/npm/Maven...). 60 req/h sans `GITHUB_TOKEN` (env), 5000/h avec. |
| CISA KEV | enrichissement | Pas une source de lignes : met à jour `tags`/`niveau_confiance`/`cve_associees` sur des `Renseignement` NVD déjà en base dont le CVE est activement exploité. |
| CNIL | normatif (RGPD) | Seule source normative réelle. |
| endoflife.date | catalogue d'actifs | N'écrit pas dans la BDP. |

**Normatif au-delà de RGPD (NIS2/ISO 27001/DORA) : pas de flux gratuit
exploitable sans inscription** (vérifié : Légifrance/EUR-Lex renvoient 403
sans compte). Prochaine étape actée avec le client : il s'inscrit sur
**piste.gouv.fr**, transmet les identifiants OAuth (jamais en dur, variable
d'env), l'intégration Légifrance se construit à ce moment-là.

`_BACKFILL_JOURS = 90` (dans `tasks.py`) : profondeur du premier run de
chaque source proactive (NVD, Ubuntu USN) — **réduite depuis 365 à la
demande du client** après un ralentissement du site pendant un premier essai
à 1 an. État actuel en base : ~102 000 renseignements (Ubuntu USN 69k, NVD
16k — backfill encore partiel, CNIL seulement 10). Ne pas relancer un
backfill volumineux sans prévenir l'utilisateur.

## Perf — leçon apprise à chaud, ne pas la refaire ailleurs

`calculer_matching()` filtre par `ILIKE` (icontains) sur `titre`,
`taxonomie_produit`, `taxonomie_editeur`, `taxonomie_referentiel`. **Sans
index trigram, ces requêtes passent en scan séquentiel dès que la table
dépasse ~10-20k lignes** — mesuré : 106ms → 3,5ms après ajout de
`pg_trgm`/`GinIndex` (migration `bdp/0006`). Si un nouveau champ texte doit
un jour être filtré par `icontains`/`ILIKE` à fort volume, penser à l'index
trigram *avant* de le déployer, pas après un ralentissement constaté par
l'utilisateur.

## Déploiement

`git push origin main` (ou `devvm main`) pousse vers le dépôt bare
(`~/repos/veille-saas.git`), un hook `post-receive` fait `git checkout -f
main` dans `~/apps/veille-saas`. **Cette étape seule ne suffit pas** si le
commit change `requirements.txt`/`settings.py`/le code des tâches Celery : le
`web` en autoreload plante en boucle sur un `ImportError` ou sert du code
obsolète tant que `worker`/`beat` n'ont pas redémarré. Séquence sûre,
toujours dans cet ordre, immédiatement après le push :
```
cd ~/apps/veille-saas && docker compose build web worker beat && docker compose up -d web worker beat
```
**Tester avant de déployer** : `git worktree add ~/dev/veille-saas-XXX main`
(ou une autre branche) + `docker build -t <tag-unique> .` + conteneur isolé
sur `--network veille-saas_internal` avec le même `.env` — **la base
Postgres est partagée** entre prod et tout conteneur de test : les écritures
de test sont réelles, les requêtes lourdes de test ralentissent la vraie
prod (vécu). Toujours arrêter/supprimer les conteneurs et process de test
une fois la vérification faite — recommandé, pas juste hygiène : la VM a
fini avec plusieurs process de test oubliés pendant des heures.

Repo GitHub : `git@github.com:Matt-PZL/mp-veille.git`, clé SSH dédiée sur la
VM (`~/.ssh/github_veille_key`, remote `github`). Le remote `origin` est le
dépôt bare local (déploiement) ; `github` est GitHub (visibilité, PR,
branches des collaborateurs).

## Pièges déjà rencontrés

- Un `{% if %}...{% else %}...{% endif %}` Django construisant un attribut
  HTML conditionnellement peut produire un guillemet manquant dans une
  branche → corrompt le HTML suivant en silence. Préférer des classes CSS
  nommées par valeur.
- `default:variable.attribut` dans un template Django plante si `variable`
  est `None` (contrairement à `{{ variable.attribut }}` seul). Toujours
  `{% if variable %}` autour d'un accès chaîné utilisé comme argument de
  filtre.
- `seed_demo` (management command) **vide et recrée** BDP/BDC/actifs à
  chaque lancement — ne jamais le lancer sur la base partagée sans y penser
  deux fois ; il a déjà pollué la BDP réelle avec des lignes factices
  (sources "ANSSI"/"ISO"/"python.org" — purgées depuis).
- Toujours créer un compte de test dédié (`qa_test` ou similaire), vérifier,
  puis **le supprimer** — motif récurrent tout au long du projet.
- Environnement Windows (poste de l'utilisateur, pas la VM) : l'outil Bash
  tourne dans un système de fichiers redirigé — les écritures vers de vrais
  chemins Windows hors de l'espace de travail échouent silencieusement,
  utiliser PowerShell pour ces cas-là.

## Accès partagés

VPN WireGuard sur la VM pour les amis collaborateurs (`tonurofa`,
`kramalow`), groupe Unix `devveille` (dépôt bare + déploiement), groupe
`docker` (= accès root de fait, décision assumée). Script
`/usr/local/sbin/ajouter-ami.sh` pour provisionner un nouveau compte + peer
VPN.
