"""Preferences de notification du compte."""

from ninja import Router

from apps.api.schemas import PreferencesOut, PreferencesWrite
from apps.bdc.models import PreferenceNotification

router = Router()


@router.get("/preferences", response=PreferencesOut)
def lire(request):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    return {"seuil_criticite": prefs.seuil_criticite, "frequence": prefs.frequence}


@router.put("/preferences", response=PreferencesOut)
def ecrire(request, donnees: PreferencesWrite):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    prefs.seuil_criticite = donnees.seuil_criticite
    prefs.frequence = donnees.frequence
    prefs.save()
    return {"seuil_criticite": prefs.seuil_criticite, "frequence": prefs.frequence}
