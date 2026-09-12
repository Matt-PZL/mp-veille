import uuid

from django.db import models


class Renseignement(models.Model):
    """
    Un renseignement de la BDP : le moment ou un renseignement public (CVE,
    bulletin CERT-FR, texte normatif...) devient un actif propriétaire.

    Jamais ecrase : si la source evolue (CVSS revise, texte amende), on cree
    une nouvelle version liee a l'original via `parent` plutot que de modifier
    en place (tracabilite = preuve d'audit).
    """

    TYPE_CHOICES = [
        ("technique", "Technique"),
        ("normatif", "Normatif"),
    ]
    CRITICITE_CHOICES = [
        ("critique", "Critique"),
        ("elevee", "Élevée"),
        ("moyenne", "Moyenne"),
        ("faible", "Faible"),
    ]

    id_renseignement_bdp = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versions"
    )

    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=500)
    description = models.TextField()

    source = models.CharField(max_length=200, help_text="ex: NVD, CERT-FR, ANSSI, ISO")
    reference_externe = models.CharField(
        max_length=200, blank=True, help_text="ex: CVE-2026-41823"
    )
    criticite = models.CharField(max_length=16, choices=CRITICITE_CHOICES, blank=True)

    # Taxonomie de rattachement — cle de lecture pour le Matching (non sensible).
    # Volet technique : categorie > editeur > produit > version.
    taxonomie_categorie = models.CharField(max_length=200, blank=True)
    taxonomie_editeur = models.CharField(max_length=200, blank=True)
    taxonomie_produit = models.CharField(max_length=200, blank=True)
    taxonomie_version = models.CharField(max_length=100, blank=True)
    # Volet normatif : referentiel (+ article/exigence en texte libre pour l'instant).
    taxonomie_referentiel = models.CharField(max_length=200, blank=True)

    decouvert_le = models.DateTimeField()
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decouvert_le"]
        indexes = [
            models.Index(fields=["taxonomie_editeur", "taxonomie_produit"]),
            models.Index(fields=["taxonomie_referentiel"]),
        ]

    def __str__(self):
        return f"{self.titre} ({self.id_renseignement_bdp})"
