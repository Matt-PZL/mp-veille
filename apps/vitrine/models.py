"""
Donnees du site public (vitrine marketing) — distinctes de la BDP (renseignements)
et de la BDC (actifs/traitements client) : ce n'est ni de la threat intel, ni de
la donnee d'un client deja onboarde, juste des prises de contact commerciales.
"""

from django.db import models


class MessageContact(models.Model):
    nom = models.CharField(max_length=200)
    email = models.EmailField()
    entreprise = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    recu_le = models.DateTimeField(auto_now_add=True)
    traite = models.BooleanField(default=False)

    class Meta:
        ordering = ["-recu_le"]

    def __str__(self):
        return f"{self.nom} ({self.email}) — {self.recu_le:%d/%m/%Y}"
