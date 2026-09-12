from django.apps import AppConfig


class BdpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bdp"
    label = "bdp"
    verbose_name = "BDP — Base de donnees propriétaire"
