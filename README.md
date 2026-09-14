# Veille — SaaS de veille cyber & normative

Voir `docs/brief.md` pour le contexte produit complet. Ce README couvre la mise
en route technique.

> **Branche `NEXT-JS`** — le Panel Client est un front Next.js autonome.
> Les gabarits Django qui le servaient auparavant ont été retirés : Django ne
> fournit plus que l'API, l'admin et les tâches de collecte.

## Stack

- **Backend** : Django 5 + django-ninja (API REST typée), PostgreSQL 16, Redis,
  Celery (+ beat) pour l'ingestion asynchrone.
- **Frontend** : Next.js 16 (App Router), React 19, TypeScript, Tailwind v4.
  Pas de librairie de composants : le design system vit dans `globals.css`.
- **Auth** : cookie de session Django. Le cookie est `httpOnly` (invisible au
  JavaScript) et le CSRF est actif sur toute écriture.
- **Infra** : Docker Compose — `db`, `redis`, `web`, `worker`, `beat`, `frontend`.

## Architecture applicative

- `apps/bdp` — Base de Données Propriétaire. Écriture seule via l'ingestion,
  jamais d'écrasement (versionning parent/enfant sur `Renseignement`).
- `apps/bdc` — Base de Données Clients. `ActifClient` (clé de matching, **non
  chiffrée**) et `Traitement` (statut + `justificatif`/`plan_action`
  **chiffrés** via `apps/bdc/fields.EncryptedTextField`, Fernet).
- `apps/matching` — lecture seule sur BDP + BDC, ne déchiffre jamais rien,
  n'écrit jamais nulle part. Correspondance tolérante (canonisation, alias,
  5 paliers de confiance) — voir `apps/matching/normalisation.py`. 25 tests.
- `apps/ingestion` — tâches Celery de collecte : NVD/CVE, CERT-FR, CNIL,
  endoflife.date (catalogue d'actifs).
- `apps/catalogue` — référentiel partagé « ce qui existe dans l'IT » (~470
  produits), alimenté automatiquement.
- `apps/api` — l'API consommée par le front : schémas, routeurs, génération PDF,
  service authentifié des preuves de traitement.
- `frontend/` — le Panel Client (Next.js).

## Démarrage (développement)

```bash
cp .env.example .env   # puis compléter les secrets (voir ci-dessous)
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

| | |
|---|---|
| Panel (Next.js) | http://localhost:3000 |
| API + admin Django | http://localhost:8000 |
| Documentation API | http://localhost:8000/api/docs |

Données de démonstration : `docker compose exec web python manage.py seed_demo`.

### Générer les secrets de `.env`

```bash
# DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# BDC_ENCRYPTION_KEY (Fernet, 32 bytes urlsafe base64)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

⚠️ `BDC_ENCRYPTION_KEY` : perdre cette clé rend tous les justificatifs de
traitement illisibles, sans récupération possible. La sauvegarder hors du dépôt
**et** hors de la machine.

## Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

Différences avec la pile de développement : Django sert via Gunicorn (plus
`runserver`), le front tourne en serveur autonome Next (plus `next dev`), le
code est embarqué dans les images (plus de volume monté), `DEBUG=0`, et les
statiques sont servis par WhiteNoise.

**Ne pas fixer `NODE_ENV` pour le service frontend** : Next le positionne
lui-même selon la commande. Le figer à `development` casse le build de
production (React résolu en deux variantes → prerendu en échec).

Variables supplémentaires en production :

- `DJANGO_HTTPS=1` une fois le reverse proxy TLS en place — active HSTS et les
  cookies `Secure`. **Laisser à 0 sans certificat**, sinon la redirection
  HTTPS boucle.
- `NEXT_PUBLIC_API_URL` — lue **au build** de l'image front (Next fige les
  `NEXT_PUBLIC_*` dans le bundle) : la changer impose de reconstruire.
- `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` — l'origine publique du front.

## Ce qui reste à faire

- Reverse proxy HTTPS (rien dans la pile ne termine le TLS) et segmentation
  réseau vis-à-vis du VLAN de Fillory (voir brief section 6).
- Onboarding première connexion, notifications (les préférences se stockent
  mais rien ne les lit), réinitialisation de mot de passe.
- Référentiels normatifs au-delà de la CNIL : ISO est payant, NIS2 et DORA sont
  du texte EUR-Lex sans flux exploitable simplement.
- Tests hors `apps/matching` (vues API, ingestion, chiffrement).
- Sortir `collecter_catalogue_actifs` du cycle de 12 h : ~470 appels HTTP
  séquentiels pour une donnée qui bouge une fois par mois.
