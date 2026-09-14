from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = "api"

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/inscription/", views.inscription, name="inscription"),
    path("auth/moi/", views.moi, name="moi"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("renseignements/", views.renseignements_list, name="renseignements"),
    path("actifs/", views.actifs_list, name="actifs"),
    path("catalogue/", views.catalogue_search, name="catalogue"),
]
