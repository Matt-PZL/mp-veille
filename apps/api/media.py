"""
Service des fichiers televerses (preuves de traitement).

Ces fichiers sont de la donnee BDC : une preuve de cloture peut contenir des
informations d'infrastructure. Les servir depuis un dossier public les
rendrait accessibles a quiconque devine l'URL — on les sert donc derriere
l'authentification.

En developpement, Django s'en chargeait via `static()` dans config/urls.py,
qui est desactive des que DEBUG=0 : sans cette vue, les preuves seraient
tout simplement introuvables en production.

Un acces non authentifie recoit un 403, pas une redirection : cette URL est
consommee par le front Next.js, qui gere lui-meme sa page de connexion — une
redirection vers un formulaire Django lui renverrait du HTML inattendu.
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden


def servir_media(request, chemin: str):
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentification requise.")

    racine = Path(settings.MEDIA_ROOT).resolve()
    cible = (racine / chemin).resolve()

    # Barriere anti-traversee : un chemin comme "../../etc/passwd" doit sortir
    # de la racine et etre refuse.
    if not cible.is_relative_to(racine) or not cible.is_file():
        raise Http404("Fichier introuvable.")

    return FileResponse(cible.open("rb"))
