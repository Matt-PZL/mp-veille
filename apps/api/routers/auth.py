"""Connexion / deconnexion / compte courant.

Auth par cookie de session Django : le cookie est httpOnly, donc invisible
au JavaScript du front — un token en localStorage ne l'aurait pas ete.
Le front doit envoyer `credentials: "include"` et le jeton CSRF sur les
requetes qui ecrivent.
"""

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from ninja import Router

from apps.api.schemas import ConnexionIn, MessageOut, UtilisateurOut

router = Router()


@router.get("/csrf", response=MessageOut, auth=None)
def csrf(request):
    """Pose le cookie CSRF. Le front l'appelle au demarrage, avant toute
    requete d'ecriture."""
    get_token(request)
    return {"detail": "ok"}


@router.post("/connexion", response={200: UtilisateurOut, 401: MessageOut}, auth=None)
def connexion(request, donnees: ConnexionIn):
    utilisateur = authenticate(request, username=donnees.username, password=donnees.password)
    if utilisateur is None:
        return 401, {"detail": "Identifiants incorrects."}
    login(request, utilisateur)
    return 200, {"username": utilisateur.username, "email": utilisateur.email or ""}


@router.post("/deconnexion", response=MessageOut)
def deconnexion(request):
    logout(request)
    return {"detail": "Déconnecté."}


@router.get("/moi", response={200: UtilisateurOut, 401: MessageOut}, auth=None)
def moi(request):
    """Sert au front a savoir s'il y a une session active, sans 401 bruyante
    au premier chargement."""
    if not request.user.is_authenticated:
        return 401, {"detail": "Non authentifié."}
    return 200, {"username": request.user.username, "email": request.user.email or ""}
