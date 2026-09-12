from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.renseignements, name="renseignements"),
    path("traitement/", views.traitement, name="traitement"),
    path("traitement/<int:pk>/marquer/", views.marquer_traitement, name="marquer_traitement"),
    path("actualites/", views.actualites, name="actualites"),
    path("organisation/", views.organisation, name="organisation"),
    path("profil/", views.profil, name="profil"),
]
