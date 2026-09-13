"""
Catalogue de reference des actifs declarables (categorie > editeur > produit
> versions connues).

Contrairement a la BDP (renseignements de securite) ou la BDC (actifs et
traitements du client), ce catalogue n'est ni proprietaire ni client : c'est
un referentiel PARTAGE de "qu'est-ce qui existe dans le monde IT", alimente
automatiquement (cf. apps.ingestion.tasks.collecter_catalogue_actifs) pour
que le client trouve toujours son actif au lieu de dependre d'une liste
tapee a la main. Un petit jeu d'entrees manuelles (`source="manuel"`) vient
combler les trous connus de la source automatique (ex : appliances reseau
non couvertes par endoflife.date).
"""

from django.db import models


class ActifCatalogueProduit(models.Model):
    SOURCE_CHOICES = [
        ("endoflife", "endoflife.date"),
        ("manuel", "Ajout manuel"),
    ]

    categorie = models.CharField(max_length=200)
    editeur = models.CharField(max_length=200)
    produit = models.CharField(max_length=200)

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manuel")
    identifiant_source = models.CharField(
        max_length=200, blank=True, help_text="ex: slug endoflife.date ('debian', 'ubuntu')"
    )
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categorie", "editeur", "produit"]
        constraints = [
            models.UniqueConstraint(
                fields=["categorie", "editeur", "produit"], name="uniq_categorie_editeur_produit"
            )
        ]
        indexes = [models.Index(fields=["editeur", "produit"])]

    def __str__(self):
        return f"{self.editeur} — {self.produit}"


class ActifCatalogueVersion(models.Model):
    """Une version connue d'un produit du catalogue, avec son etat de
    maintenance — sert a proposer les versions disponibles a la saisie
    (au lieu d'un champ texte libre) et a signaler une version en fin de vie."""

    produit = models.ForeignKey(
        ActifCatalogueProduit, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.CharField(max_length=100)
    label = models.CharField(max_length=200, blank=True)
    maintenue = models.BooleanField(default=True)
    sortie_le = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-sortie_le", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["produit", "version"], name="uniq_produit_version")
        ]

    def __str__(self):
        return f"{self.produit} {self.version}"
