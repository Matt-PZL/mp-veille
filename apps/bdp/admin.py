from django.contrib import admin

from .models import Renseignement


@admin.register(Renseignement)
class RenseignementAdmin(admin.ModelAdmin):
    list_display = ("titre", "type", "criticite", "source", "decouvert_le")
    list_filter = ("type", "criticite", "source")
    search_fields = ("titre", "description", "reference_externe", "id_renseignement_bdp")
    readonly_fields = ("id_renseignement_bdp", "cree_le")
