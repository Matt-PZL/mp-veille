"""
Champ chiffre pour la BDC.

Regle d'architecture (voir brief section 6/7) : le Matching ne doit jamais
avoir a dechiffrer une fenetre large de donnees clients. Les champs chiffres
via EncryptedTextField portent donc uniquement les metadonnees sensibles
(justificatifs, commentaires) — jamais les cles de taxonomie/statut qui
servent au Matching, qui restent en clair (voir apps/bdc/models.py).

Le dechiffrement n'a lieu qu'au moment de l'affichage dans le Panel Client,
pour l'utilisateur authentifie proprietaire de la donnee.
"""

from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = settings.BDC_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """TextField chiffre au repos avec Fernet (AES-128-CBC + HMAC)."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Valeur non chiffree (donnee de migration/seed) ou mauvaise cle.
            return value
