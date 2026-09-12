# Veille — SaaS de veille cyber & normative

Voir `docs/brief.md` pour le contexte produit complet. Ce README couvre uniquement la mise en route technique.

## Stack

- **Backend** : Django 5, PostgreSQL 16, Redis, Celery (+ beat) pour l'ingestion asynchrone.
- **Frontend** : templates Django + HTMX + Alpine.js, pas de SPA.
- **Infra** : Docker Compose (`db`, `redis`, `web`, `worker`, `beat`).
- **Déploiement** : `git push devvm main` → hook `post-receive` sur la VM qui checkout dans `~/apps/veille-saas`. Relancer les conteneurs manuellement après un changement de dépendances (voir plus bas).

## Architecture applicative

- `apps/bdp` — Base de Données Propriétaire. Écriture seule via l'ingestion, jamais d'écrasement (versionning parent/enfant sur `Renseignement`).
- `apps/bdc` — Base de Données Clients. Contient `ActifClient` (taxonomie, clé de matching, **non chiffré**) et `Traitement` (statut + `justificatif` **chiffré** via `apps/bdc/fields.EncryptedTextField`, Fernet).
- `apps/matching` — lecture seule sur BDP + BDC, ne déchiffre jamais rien, n'écrit jamais nulle part. Déclenché après ingestion ou modification de profil, jamais à l'ouverture du panel.
- `apps/ingestion` — tâches Celery de collecte (stubs pour l'instant : NVD/CVE, CERT-FR, référentiels normatifs).
- `apps/panel` — vues et templates du Panel Client (Renseignements, Traitement, Actualités, Organisation, Profil).
- `apps/accounts` — auth mono-utilisateur (login/logout/reset).

## Démarrage (sur devvm, après un premier `git push`)

```bash
cd ~/apps/veille-saas
cp .env.example .env   # puis completer les secrets (voir ci-dessous)
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### Générer les secrets de `.env`

```bash
# DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# BDC_ENCRYPTION_KEY (Fernet, 32 bytes urlsafe base64)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

⚠️ `BDC_ENCRYPTION_KEY` : perdre cette clé rend tous les justificatifs de traitement illisibles. La sauvegarder hors du dépôt et hors de la VM (gestionnaire de secrets personnel), pas seulement dans `.env`.

## Après un `git push` qui change `requirements.txt` ou le `Dockerfile`

Le hook ne fait que le checkout — il ne relance pas les conteneurs. Après un push de ce type :

```bash
ssh devvm "cd ~/apps/veille-saas && docker compose build && docker compose up -d && docker compose exec -T web python manage.py migrate"
```

## Ce qui reste à faire (voir brief section 7 pour le détail produit)

- Connecteurs d'ingestion réels (NVD/CVE, CERT-FR, ISO/CNIL/ANSSI/DORA) — `apps/ingestion/tasks.py` n'a que des stubs.
- Onboarding (déclaration d'actifs + sélection des référentiels).
- Distinction technique/normatif en arborescence dans Renseignements (actuellement un simple champ `type`).
- Graphes de Traitement (répartition par statut, tendance de clôture) — pas encore branchés sur les vraies données.
- Export PDF, filtre par plage de dates sur Traitement, notifications.
- Badge "nouveau" sur les renseignements non consultés.
