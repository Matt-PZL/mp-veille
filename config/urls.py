from django.contrib import admin
from django.urls import path, re_path

from apps.api.api import api
from apps.api.media import servir_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    # Les preuves de traitement passent par une vue authentifiee : c'est de la
    # donnee client, elle n'a pas a etre servie en clair depuis un dossier
    # public.
    re_path(r"^media/(?P<chemin>.+)$", servir_media, name="media"),
]
