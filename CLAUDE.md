# Cyrens

Plateforme SaaS de veille et renseignement cybersécurité destinée aux RSSI et aux équipes cyber.

## Objectif

Réduire le temps consacré à la veille cybersécurité tout en fournissant un suivi contextualisé basé sur les actifs réels du client.

---

# Lecture du contexte

Toujours lire :

- docs/project/current-state.md

Lire uniquement si nécessaire :

- docs/technical/architecture.md
- docs/technical/conventions.md
- docs/technical/decisions.md
- docs/product/vision.md

Ne jamais parcourir l'ensemble du repository sans demande explicite.

Avant de lire de nouveaux fichiers :
- vérifier qu'ils sont nécessaires à la tâche
- privilégier l'information déjà disponible

---

# Architecture validée

Les choix suivants sont considérés comme actés :

- Backend : Django
- API : Django Ninja
- Frontend : Next.js
- Base de données : PostgreSQL
- Cache / file d'attente : Redis
- Tâches asynchrones : Celery
- BDP indépendante de la BDC
- Matching en lecture seule

Ne pas proposer de refonte architecturale sans demande explicite.

---

# Travail collaboratif

Plusieurs développeurs travaillent sur ce dépôt.

- Ne modifier que les fichiers nécessaires à la tâche.
- Ne jamais modifier un fichier sans nécessité directe.
- Ne jamais effectuer de réécriture massive.
- Ne jamais effectuer de refactor global non demandé.
- Privilégier les changements localisés et ciblés.
- Ne jamais corriger des problèmes hors périmètre de la tâche en cours.

---

# Git

Interdiction de :

- git commit
- git push
- git pull
- git merge
- git rebase
- git reset
- git stash
- création de branche
- suppression de branche

Claude peut consulter l'état Git mais ne doit jamais modifier l'historique.

Toute opération Git est réalisée par un humain.

---

# Commandes système

Ne jamais exécuter de commande destructive sans demande explicite :

- rm
- rmdir
- del
- docker compose down -v
- docker system prune
- suppression de volumes
- suppression de bases de données

Toujours demander confirmation avant toute action irréversible.

---

# Base de données

Ne jamais exécuter :

- migrations
- seed
- scripts destructifs
- suppression de données

sans demande explicite.

Les migrations peuvent être proposées mais jamais exécutées automatiquement.

---

# Dépendances

Ne jamais :

- installer une dépendance
- modifier requirements.txt
- modifier package.json
- modifier docker-compose.yml

sans validation explicite.

Toute nouvelle dépendance doit être justifiée.

---

# Méthode de travail

Pour chaque tâche :

1. Comprendre l'objectif.
2. Identifier les fichiers concernés.
3. Lire uniquement ces fichiers.
4. Proposer une approche concise.
5. Implémenter.
6. Vérifier les impacts.
7. Mettre à jour la documentation si nécessaire.

---

# Simplicité

Toujours privilégier :

- la solution la plus simple
- la modification de l'existant
- le moindre nombre de fichiers
- le moindre nombre d'abstractions

Ne pas introduire de complexité anticipée.

---

# Cas de doute

Ne jamais supposer.

Demander une clarification pour :

- sécurité
- chiffrement
- déploiement
- infrastructure
- suppression de données
- modifications architecturales

---

# Performance de contexte

Ne jamais analyser le dépôt complet.

Ne jamais lancer d'audit global sans demande explicite.

Ne jamais relire des fichiers déjà suffisants pour accomplir la tâche.

Privilégier l'analyse ciblée à l'analyse exhaustive.

---

# Fin de tâche

Toujours fournir :

- les fichiers modifiés
- un résumé des changements
- les impacts éventuels
- les points nécessitant une validation humaine

Mettre à jour docs/project/current-state.md si la tâche modifie l'état du projet.