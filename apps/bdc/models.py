from django.conf import settings
from django.db import models

from .fields import EncryptedTextField


class ActifClient(models.Model):
    """
    Actif technique ou referentiel normatif declare/suivi par le client.

    Sert de cle de matching (non sensible) : le Matching ne lit que ces
    champs de taxonomie, jamais les champs chiffres de Traitement.
    """

    TYPE_CHOICES = [
        ("technique", "Technique"),
        ("normatif", "Normatif"),
    ]

    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    categorie = models.CharField(max_length=200, blank=True)
    editeur = models.CharField(max_length=200, blank=True)
    produit = models.CharField(max_length=200, blank=True)
    version = models.CharField(max_length=100, blank=True)
    referentiel = models.CharField(max_length=200, blank=True)

    ajoute_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["editeur", "produit"])]

    def __str__(self):
        return self.produit or self.referentiel or self.categorie or f"actif#{self.pk}"


class Traitement(models.Model):
    """
    Action de traitement d'un renseignement par le client. Ecrit directement
    ici (jamais via le Matching, qui est lecture seule sur BDP+BDC).
    """

    STATUT_CHOICES = [
        ("a_traiter", "À traiter"),
        ("en_cours", "Démarré"),
        ("clos", "Clos"),
        ("non_applicable", "Non applicable"),
    ]

    # Reference non sensible vers la BDP — pas de ForeignKey cross-app/cross-DB,
    # juste l'UUID stable id_renseignement_bdp.
    id_renseignement_bdp = models.UUIDField(db_index=True)
    actif = models.ForeignKey(
        ActifClient, null=True, blank=True, on_delete=models.SET_NULL, related_name="traitements"
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="a_traiter")
    # Sensible -> chiffre. "clos" et "non_applicable" l'exigent (voir apps/panel).
    # Sert de justificatif general ET de "preuve texte" a la cloture.
    justificatif = EncryptedTextField(blank=True, default="")
    echeance = models.DateField(null=True, blank=True, help_text="Date previsionnelle de traitement")

    # --- Champs specifiques au statut "Démarré" ---
    plan_action = EncryptedTextField(blank=True, default="")
    passage_cab = models.BooleanField(
        null=True, blank=True, help_text="Oui/Non — non renseigne si null"
    )

    # --- Champ specifique au statut "Clos" (preuve fichier, optionnelle) ---
    preuve_fichier = models.FileField(upload_to="preuves/%Y/%m/", null=True, blank=True)

    maj_le = models.DateTimeField(auto_now=True)

    @property
    def en_retard(self):
        from django.utils import timezone
        return bool(
            self.echeance
            and self.echeance < timezone.localdate()
            and self.statut in ("a_traiter", "en_cours")
        )

    class Meta:
        indexes = [
            models.Index(fields=["id_renseignement_bdp"]),
            models.Index(fields=["statut"]),
        ]

    def __str__(self):
        return f"{self.id_renseignement_bdp} — {self.get_statut_display()}"


class HistoriqueTraitement(models.Model):
    """Mini-timeline horodatee : decouverte -> prise en charge -> cloture."""

    traitement = models.ForeignKey(Traitement, on_delete=models.CASCADE, related_name="historique")
    evenement = models.CharField(max_length=100)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["horodatage"]

    def __str__(self):
        return f"{self.evenement} @ {self.horodatage:%d/%m/%Y %H:%M}"


class PreferenceNotification(models.Model):
    """Preferences de notification liees au profil utilisateur (mono-utilisateur pour ce POC)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences")
    seuil_criticite = models.CharField(
        max_length=16,
        choices=[("critique", "Critique"), ("elevee", "Élevée et plus"), ("moyenne", "Moyenne et plus")],
        default="elevee",
    )
    frequence = models.CharField(
        max_length=16,
        choices=[("immediat", "Immediat"), ("quotidien", "Quotidien"), ("hebdo", "Hebdomadaire")],
        default="quotidien",
    )
    # Pastilles de compteur (Renseignements 13, Actifs 2...) dans la barre de
    # navigation : toujours affichees ou jamais, au choix du client — cf.
    # Profil > Apparence.
    afficher_compteurs_nav = models.BooleanField(default=True)


class RenseignementConsulte(models.Model):
    """Marque de lecture cote client. C'est un fait propre au client (a-t-il
    ouvert ce renseignement ?), donc BDC et non BDP, meme si la cle pointe
    vers un id_renseignement_bdp."""

    id_renseignement_bdp = models.UUIDField(unique=True)
    consulte_le = models.DateTimeField(auto_now_add=True)


class HistoriqueActif(models.Model):
    """Journal des ajouts/modifications/suppressions d'actifs (page Gestion
    des actifs). `actif_repr` est un instantane texte car l'actif peut avoir
    ete supprime au moment ou on consulte l'historique."""

    EVENEMENT_CHOICES = [
        ("ajout", "Ajouté"),
        ("version", "Version modifiée"),
        ("suppression_conserve", "Retiré (historique conservé)"),
        ("suppression_purge", "Retiré (historique purgé)"),
    ]

    actif_repr = models.CharField(max_length=300)
    evenement = models.CharField(max_length=30, choices=EVENEMENT_CHOICES)
    detail = models.CharField(max_length=300, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.get_evenement_display()} — {self.actif_repr}"


class ActionHistorique(models.Model):
    """Journal unifie de tout ce qui a affecte le perimetre client : ajout /
    modification / suppression dun actif, ou dun traitement.

    Distinct de HistoriqueActif/HistoriqueTraitement (conserves tels quels,
    ils alimentent chacun leur propre ecran) : celui-ci existe uniquement
    pour le panneau "Historique des actions" de Renseignements, qui doit
    pouvoir tout melanger et trier par date quel que soit le type dobjet.
    Chaque mutation ecrit ici EN PLUS de son historique specifique, jamais a
    la place.

    objet_repr est un instantane texte (pas de FK) : lobjet peut avoir ete
    supprime au moment ou on consulte le journal.
    """

    TYPE_OBJET_CHOICES = [
        ("actif", "Actif"),
        ("traitement", "Traitement"),
    ]
    ACTION_CHOICES = [
        ("ajout", "Ajout"),
        ("modification", "Modification"),
        ("suppression", "Suppression"),
    ]

    type_objet = models.CharField(max_length=20, choices=TYPE_OBJET_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    objet_repr = models.CharField(max_length=300)
    detail = models.CharField(max_length=300, blank=True)
    utilisateur = models.CharField(max_length=150, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.get_action_display()} {self.get_type_objet_display()} — {self.objet_repr}"
