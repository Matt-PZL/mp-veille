# Brief technique — SaaS de veille cyber & normative
*Document de handoff pour reprise en développement. Contexte complet ci-dessous ; pas besoin de poser de questions sur le "pourquoi", seulement sur les choix techniques encore ouverts (voir section finale).*

## 1. Le produit en une phrase
Un SaaS qui fait de la veille sur les actifs techniques d'une entreprise (CVE, bulletins CERT-FR) **et** sur les référentiels normatifs qu'elle suit (ISO 27001, RGPD, NIS2, DORA), avec la même mécanique de collecte pour les deux, et une traçabilité complète des actions qui sert elle-même de preuve d'audit ISO 27001 (pas de module de conformité séparé — c'est la méthodologie de veille qui répond à l'exigence).

Cible pilote : une ESN avec un gros SI et beaucoup d'actifs applicatifs. Équipe : trois personnes (Data/Power BI, Infra/DevSecOps, Cybersécurité/GRC), side-project en plus d'un emploi à 37h/semaine.

**Concurrent direct identifié** : TechWatchAlert (français, self-service, 19-39€/mois) fait déjà la partie technique (CVE/EOL) très bien. Il ne couvre **pas** le volet référentiels normatifs — c'est notre différenciateur principal, à ne jamais diluer.

## 2. Flux de données (architecture logique, indépendante des technos)

```
Ingestion → Normalisation → BDP (Base de Données Propriétaire)
                                      ↓
Users → Panel Client ↔ BDC (Base de Données Clients) → Matching ← (lit BDP + BDC)
                                                            ↓
                                                    résultat → Panel Client
```

- **Ingestion** : collecte en boucle (ex. 12h) sur des sources précises (CVE/NVD, CERT-FR/ANSSI, textes normatifs ISO/CNIL/ANSSI/DORA)
- **Normalisation** : format standard (source, date, résumé, tags, criticité), pensé pour ce que le panel devra afficher
- **BDP** : écriture via API interne sécurisée. C'est le moment où un renseignement public devient un actif propriétaire. Chaque item a un **id stable** (`id_renseignement_bdp`) dès sa création. **Jamais écrasé** : si la source évolue (CVSS révisé, texte amendé), une nouvelle version est créée, liée à l'original en **parent/enfant**. Pas de chiffrement par client nécessaire ici (donnée mutualisée, non spécifique à un client).
- **BDC** : profil client (actifs déclarés + référentiels suivis) **et** historique/traçabilité de ses actions. **Chiffrement fort exigé ici** (voir section contraintes).
- **Matching** : prend **BDP + BDC** en lecture seule, n'écrit **jamais** nulle part. Renvoie un résultat au panel avec l'`id_renseignement_bdp` de chaque item pertinent.
  - Déclenché (a) après chaque cycle d'ingestion, (b) immédiatement après une modification de profil client. **Jamais** à l'ouverture du panel — le panel affiche le dernier résultat déjà calculé.
- **Panel Client** : le client y déclare son profil et y traite les renseignements. Une action de traitement écrit directement `(id_client, id_renseignement_bdp, statut, horodatage[, justificatif])` dans la BDC — sans jamais passer par le Matching pour ce cas.

## 3. Discovery des actifs (3 méthodes retenues)
- **Déclaratif manuel** : taxonomie fournie (catégorie → éditeur → produit → version), le client coche
- **Import CSV** : mapping vers la taxonomie interne
- **Connecteurs API** (V2, pas dans ce lot) : Microsoft Graph en premier (Azure AD, Defender, Intune, M365)

Pas de scan actif, pas d'agent installé (délibérément écarté — c'est le métier d'un VOC, pas de la veille).

Point de vigilance taxonomie : les termes génériques ("Pare-feu", "SQL") doivent descendre au niveau éditeur/produit (ex. "Palo Alto PAN-OS", "PostgreSQL") pour générer une veille exploitable.

## 4. Écrans du Panel Client

Toutes les listes suivent le même schéma : **un axe de catégorie à gauche qui filtre, une liste dense à droite qui s'affiche en fonction, chaque ligne cliquable qui s'ouvre en accordéon vers le bas (jamais en modal, jamais ailleurs)**. Les en-têtes de colonnes sont eux-mêmes les contrôles de tri (pas de boutons séparés) — l'alignement colonne/contenu doit être garanti par une grille CSS partagée entre l'en-tête et les lignes.

### Renseignements sur les actifs
- **Axe gauche** : liste des actifs (triable A-Z ou par nombre de renseignements), avec "Tous les actifs" par défaut
- **Colonnes droite** : Renseignement | Traitement | Date
- **Statut par défaut** : `+ Traitement` (pastille en pointillé, visuellement distincte d'un statut posé — un statut doit toujours résulter d'une action volontaire, jamais d'une valeur préremplie anonyme)
- **Statuts possibles** : À traiter (le défaut ci-dessus une fois choisi explicitement) / En cours de traitement / Clos / Non applicable — les deux derniers exigent un **justificatif**, affiché en italique sous la pastille dans la liste
- **Détail déplié** : Description (pleine largeur) puis, côte à côte, Sources | Découvert le
- **Encore à ajouter** (validé avec le client, pas encore mocké) :
  - Distinguer visuellement technique / normatif — le client envisage une présentation en "dossiers"/arborescence par type plutôt qu'une simple couleur
  - Badge "nouveau" sur les renseignements jamais consultés

### Traitement
- **Axe gauche** : les 4 statuts (Tous / À traiter / En cours / Clos / Non applicable), avec compteur
- **Colonnes droite** : **Actif d'abord, puis Renseignement** (même poids visuel pour les deux, pas de texte grisé pour l'actif) — **pas de colonne Date ici**
- **Détail déplié** : Statut, Justificatif (si applicable), **Historique** (mini-timeline verticale : découverte → prise en charge → clôture, horodatée), Actions (bouton qui change selon le statut : "Marquer traité" / "Clôturer"), **Exporter en PDF**, et un lien **"Voir le renseignement →"** qui redirige vers l'écran Renseignements plutôt que de dupliquer les infos ici
- **En bas de page** (hors du tableau, avec ses propres marges) : des graphes simples — répartition par statut, tendance de clôture sur plusieurs semaines
- **Encore à ajouter** (validé avec le client, pas encore mocké) :
  - Filtre par plage de dates (c'est l'écran preuve d'audit — un auditeur demande "tout ce qui a été traité sur telle période")
  - Délai de traitement prévisionnel + rappels/notifications
  - Export global (tout ce qui est filtré) en plus de l'export par item

### Actualités
Flux complet de la BDP, **non filtré sur les actifs déclarés** — pas d'axe de gauche. Sert à montrer la valeur de la base de connaissance au-delà du périmètre strict du client.

### Gestion de l'organisation
Actifs et référentiels suivis : ajout/retrait. Au retrait d'un actif, le client choisit explicitement de **conserver ou purger** l'historique de traitement associé.

### Gestion du profil
Compte utilisateur (email, mot de passe) + préférences de notification (seuil de criticité, fréquence des alertes — lié aux rappels/notifications de l'écran Traitement).

### Onboarding
Traversé une seule fois, à la première connexion : déclaration des actifs + sélection des référentiels suivis.

### Hors panel
Connexion / inscription / mot de passe oublié.

## 5. Direction visuelle retenue
**Ambiance : "renseignement stratégique" — futuriste mais sérieux, esprit salle de briefing/état plutôt que hacker ou SaaS grand public.**

- Fond très sombre quasi-noir : `#0A0D13` / panneaux `#0F131B` / bordures `#1E2530`
- **Texte principal : blanc pur `#FFFFFF`** (pas de blanc cassé — lisibilité avant tout)
- **Accent unique : `#2667FF`** (bleu électrique)
- Fond avec un **quadrillage très fin** façon carte/radar tactique, en dérivé de l'accent à faible opacité (`rgba(38,103,255,0.07)`), pas du gris neutre
- **Coins en L façon HUD/réticule** sur les conteneurs principaux (les tableaux, les cartes de graphe) — pas sur chaque ligne individuelle, pour ne pas faire de bruit visuel
- Typographie : **Archivo** (700) pour les titres, **IBM Plex Sans** pour le texte courant, **IBM Plex Mono** pour tout ce qui fait identifiant/code/date (CVE-XXXX, `id_renseignement_bdp`, timestamps)
- Vocabulaire "dossier" plutôt que générique : les tags de source peuvent être stylés façon "SOURCE: NVD" en mono, cohérent avec l'esprit du produit
- **Densité avant décoration** : tableaux/listes serrés, pas de gros cards, pas de kanban, pas de widgets illustratifs gratuits. Les tableaux doivent être **bien centrés avec de belles marges**, jamais en pleine largeur façon dashboard de monitoring (Grafana-like à éviter explicitement)

### Fichiers de référence visuelle (mockups HTML fonctionnels, à donner tels quels à Claude Code comme référence de structure ET de style)
- `theme-final.html` — dernière version stylée des écrans Renseignements + Traitement (structure ET couleurs validées, mais **un bug de rendu signalé par le client reste à vérifier/corriger** — le fichier n'a pas encore été confirmé comme correct après la dernière correction des coins HUD)
- `structure-master-list.html` — structure de référence de "Renseignements" (avant thème, plus simple à lire pour la logique JS)
- `traitement-mockup.html` — structure de référence de "Traitement"
- `landing-page-v2.html` — première direction de landing page (structure à revalider avec la nouvelle direction visuelle "renseignement stratégique" — pas encore réappliquée dessus)
- `panel-client-mockup.html` — tout premier mockup (obsolète, gardé pour historique de la réflexion uniquement)

**Important : ces fichiers sont du HTML/CSS/JS statique de mockup, pas du code de production.** Aucun n'a de vraie logique serveur, de base de données, ni d'auth. Ils servent uniquement de référence de structure et de style à reproduire dans un vrai framework.

## 6. Contraintes actées pour cette phase
- **Chiffrement avancé dès le départ** sur la BDC (pas repoussé en V2). Point d'architecture non tranché : comment le Matching lit des données chiffrées sans exposer une fenêtre en clair trop large — déchiffrement en mémoire au moment du matching, ou matching sur des identifiants de taxonomie non sensibles avec chiffrement réservé aux métadonnées. **À trancher avec Claude Code.**
- **Hébergement en homelab perso** (infra existante : un honeypot nommé Fillory, sur un réseau segmenté par nftables). **Le nouveau projet doit être isolé du VLAN/segment de Fillory** — Fillory est volontairement exposé aux attaquants, le SaaS ne doit jamais partager son segment réseau.
- **Mono-utilisateur** par entreprise cliente pour ce POC (pas de multi-comptes par organisation pour l'instant)
- **Pas d'API client-facing**, pas de facturation/paiement pour cette phase
- **Architecture Celery + Redis** déjà actée pour la collecte asynchrone

## 7. Ce qui n'est PAS encore tranché (à décider avec Claude Code, pas à deviner)
- Framework backend (Django / FastAPI / autre)
- Framework frontend (le client a testé des mockups HTML/CSS/JS vanilla ; rien n'indique une préférence React/Vue/autre)
- Implémentation précise du chiffrement (solution de secrets management type Vault vs chiffrement applicatif)
- Détail technique de la distinction technique/normatif dans "Renseignements" (arborescence par dossier évoquée par le client, pas encore spécifiée)
- Détail des graphes de "Traitement" (lib de charting à choisir)
