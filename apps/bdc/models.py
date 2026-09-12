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
        ("en_cours", "En cours de traitement"),
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
    justificatif = EncryptedTextField(blank=True, default="")

    maj_le = models.DateTimeField(auto_now=True)

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
