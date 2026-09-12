from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.vue_ensemble, name="dashboard"),
    path("renseignements/", views.renseignements, name="renseignements"),
    path(
        "renseignements/<uuid:id_renseignement_bdp>/traitement/",
        views.definir_traitement,
        name="definir_traitement",
    ),
    path(
        "renseignements/<uuid:id_renseignement_bdp>/consulter/",
        views.marquer_consulte,
        name="marquer_consulte",
    ),
    path("traitement/", views.traitement, name="traitement"),
    path("traitement/<int:pk>/marquer/", views.marquer_traitement, name="marquer_traitement"),
    path("traitement/<int:pk>/echeance/", views.definir_echeance, name="definir_echeance"),
    path("traitement/<int:pk>/pdf/", views.export_traitement_pdf, name="export_traitement_pdf"),
    path("actualites/", views.actualites, name="actualites"),
    path("organisation/", views.organisation, name="organisation"),
    path("organisation/ajouter/", views.ajouter_actif, name="ajouter_actif"),
    path("organisation/importer/", views.importer_actifs_csv, name="importer_actifs_csv"),
    path("organisation/<int:pk>/retirer/", views.retirer_actif, name="retirer_actif"),
    path("profil/", views.profil, name="profil"),
]
