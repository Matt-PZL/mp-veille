"""Preferences de notification du compte."""

from ninja import Router

from apps.api.schemas import PreferencesOut, PreferencesWrite
from apps.bdc.models import PreferenceNotification

router = Router()


def _sortie(prefs):
    return {
        "seuil_criticite": prefs.seuil_criticite,
        "frequence": prefs.frequence,
        "afficher_compteurs_nav": prefs.afficher_compteurs_nav,
    }


@router.get("/preferences", response=PreferencesOut)
def lire(request):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    return _sortie(prefs)


@router.put("/preferences", response=PreferencesOut)
def ecrire(request, donnees: PreferencesWrite):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    prefs.seuil_criticite = donnees.seuil_criticite
    prefs.frequence = donnees.frequence
    prefs.afficher_compteurs_nav = donnees.afficher_compteurs_nav
    prefs.save()
    return _sortie(prefs)
