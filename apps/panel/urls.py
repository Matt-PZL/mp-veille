from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.vue_ensemble, name="dashboard"),
    path("actifs/", views.gestion_actifs, name="gestion_actifs"),
    path("actifs/ajouter/", views.ajouter_actif, name="ajouter_actif"),
    path("actifs/importer/", views.importer_actifs_csv, name="importer_actifs_csv"),
    path("actifs/exporter/", views.exporter_actifs_csv, name="exporter_actifs_csv"),
    path("actifs/<int:pk>/version/", views.monter_version_actif, name="monter_version_actif"),
    path("actifs/<int:pk>/retirer/", views.retirer_actif, name="retirer_actif"),
    path("renseignements/", views.renseignements, name="renseignements"),
    path(
        "renseignements/<uuid:id_renseignement_bdp>/traiter/",
        views.traiter_renseignement,
        name="traiter_renseignement",
    ),
    path(
        "renseignements/<uuid:id_renseignement_bdp>/consulter/",
        views.marquer_consulte,
        name="marquer_consulte",
    ),
    path("traitement/", views.traitement, name="traitement"),
    path("traitement/<int:pk>/echeance/", views.definir_echeance, name="definir_echeance"),
    path("traitement/<int:pk>/pdf/", views.export_traitement_pdf, name="export_traitement_pdf"),
    path("actualites/", views.actualites, name="actualites"),
    path("organisation/", views.organisation, name="organisation"),
    path("profil/", views.profil, name="profil"),
]
