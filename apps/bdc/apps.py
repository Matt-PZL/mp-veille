from django.apps import AppConfig


class BdcConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bdc"
    label = "bdc"
    verbose_name = "BDC — Base de donnees clients"
