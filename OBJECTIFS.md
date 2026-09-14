# Objectifs du projet — pourquoi Veille existe

Fichier séparé de `CLAUDE.md` volontairement : ceci décrit *pourquoi* le
produit existe et ce qu'il doit garantir, pas *comment* le code est fait
aujourd'hui. À consulter avant de trancher un choix produit ambigu (est-ce
que telle simplification technique casse un objectif ? Vérifier ici avant
de décider seul).

## Ce que c'est

SaaS de veille cyber + conformité réglementaire, développé pour une ESN. La
landing page publique (page d'accueil, pricing, inscription en self-service)
indique une vocation commerciale réelle, pas seulement un outil interne —
mais le modèle de tarification précis et le marché cible exact n'ont pas
été formalisés dans cette conversation : à confirmer avec l'utilisateur
plutôt qu'à deviner si une décision produit en dépend.

## Le problème que ça résout

Les flux de veille cyber bruts (NVD, CERT-FR...) sont trop bruyants pour
être exploitables tels quels — des milliers d'alertes par semaine, la
plupart sans rapport avec ce qu'une entreprise exploite réellement. Un
analyste ou un RSSI n'a pas le temps de tout trier à la main. Le produit
répond à ça : le client déclare précisément son parc (actifs techniques +
référentiels normatifs suivis), et seul ce qui le concerne vraiment lui est
remonté — avec une justification explicite ("pourquoi ce renseignement vous
est remonté : correspondance exacte avec un de vos actifs").

## Le principe fondateur, et pourquoi il ne doit jamais être contourné

BDP (renseignements) et BDC (actifs + traitements par client) sont
volontairement séparées, reliées uniquement par le Matching (lecture seule).
Objectif produit derrière ce choix, pas juste une préférence technique : la
BDP doit devenir une base de threat intelligence **massive et autonome**
(plusieurs sources indépendantes, jamais limitée à ce qu'un client a
déclaré — cf. l'épisode "pas d'OpenSSH" qui a motivé la bascule de
l'ingestion NVD en proactif), pendant que chaque client garde une vue
strictement scopée à son propre périmètre. Le même moteur doit pouvoir
servir n'importe quel nombre de clients sans jamais mélanger leurs données
ni leur montrer du bruit. Une "simplification" qui recouplerait
l'ingestion à un client particulier (comme l'ancien `collecter_nvd_cve`
reactif) va à l'encontre de cet objectif, même si elle est plus simple à
coder.

## Ce qui doit rester vrai, quelle que soit l'implémentation

- **Aucune donnée inventée en production.** Uniquement des sources réelles,
  vérifiées avant intégration (la purge des lignes `seed_demo` mélangées à
  la vraie BDP en est l'illustration directe).
- **Zéro doublon dans la BDP**, quelle que soit la source — exigence
  explicite du client, avec garde-fou en base (pas seulement applicatif).
- **Chaque décision de traitement fait preuve d'audit** : statut,
  justificatif, date, horodatage — le produit vise explicitement à outiller
  une démarche de conformité (ISO 27001 nommément cité dans le produit,
  RGPD/NIS2/DORA côté normatif).
- **Traçabilité des actions** : qui a ajouté/modifié/supprimé un actif ou un
  traitement, et quand — pas seulement le contenu final.

## Ambitions actées, pas encore réalisées

- Couverture normative au-delà du RGPD (NIS2, ISO 27001, DORA) — bloquée
  sur l'absence de flux public gratuit exploitable ; la voie identifiée est
  une inscription du client sur le portail PISTE (Légifrance), en attente.
- Migration complète du frontend vers Next.js (`next-migration`), pas
  encore fusionnée dans `main` ni déployée en production.
- Vrai multi-utilisateur par client : le code note encore "mono-utilisateur
  pour ce POC" à plusieurs endroits (ex. préférences de notification) — à
  garder en tête si le produit doit un jour servir plusieurs analystes chez
  un même client.

## Ce qui n'est pas encore défini — à demander, pas à supposer

- Modèle de tarification précis (une section pricing existe sur la landing
  page, contenu indicatif).
- Marché cible exact au-delà de "clients d'une ESN" (taille d'entreprise,
  secteur).
- Échéance ou jalon de lancement commercial.
