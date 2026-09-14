"""
Point d'entree de l'API consommee par le front Next.js.

Auth par cookie de session Django : `django_auth` verifie que la session
portee par le cookie est authentifiee.

Le CSRF est actif : django-ninja 1.x l'active par defaut sur toute auth par
cookie (APIKeyCookie.__init__ prend csrf=True). C'est indispensable ici —
sans lui, n'importe quel site tiers pourrait declencher une ecriture au nom
de l'utilisateur connecte, puisque le navigateur joindrait le cookie tout
seul. Ne pas passer `csrf=` a NinjaAPI : l'argument n'existe plus en 1.x.
"""

from ninja import NinjaAPI
from ninja.security import django_auth

from apps.api.routers import actifs, auth, dashboard, journal, profil, renseignements, traitement

api = NinjaAPI(
    title="Veille — API",
    version="1.0.0",
    description="API du panel de veille cyber & normative.",
    auth=django_auth,
)

api.add_router("/auth", auth.router, tags=["auth"])
api.add_router("/dashboard", dashboard.router, tags=["dashboard"])
api.add_router("/renseignements", renseignements.router, tags=["renseignements"])
api.add_router("/traitements", traitement.router, tags=["traitement"])
api.add_router("/actifs", actifs.router, tags=["actifs"])
api.add_router("/profil", profil.router, tags=["profil"])
api.add_router("/journal", journal.router, tags=["journal"])
