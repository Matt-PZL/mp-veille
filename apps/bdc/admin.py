from django.contrib import admin

from .models import ActifClient, HistoriqueTraitement, PreferenceNotification, Traitement


@admin.register(ActifClient)
class ActifClientAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type", "editeur", "referentiel", "ajoute_le")
    list_filter = ("type",)


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueTraitement
    extra = 0
    readonly_fields = ("horodatage",)


@admin.register(Traitement)
class TraitementAdmin(admin.ModelAdmin):
    list_display = ("id_renseignement_bdp", "actif", "statut", "maj_le")
    list_filter = ("statut",)
    inlines = [HistoriqueInline]


@admin.register(PreferenceNotification)
class PreferenceNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "seuil_criticite", "frequence")
