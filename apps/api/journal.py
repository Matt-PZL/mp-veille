"""
Consignation dans le journal d'actions unifie (ActionHistorique).

Point d'entree unique appele depuis chaque site de mutation (actifs.py,
traitement.py) : garantit que le format (utilisateur, horodatage) reste le
meme partout, et evite de dupliquer la lecture de request.user a chaque
appel.
"""

from __future__ import annotations

from apps.bdc.models import ActionHistorique


def consigner(request, *, type_objet: str, action: str, objet_repr: str, detail: str = "") -> None:
    utilisateur = ""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        utilisateur = user.username

    ActionHistorique.objects.create(
        type_objet=type_objet,
        action=action,
        objet_repr=objet_repr,
        detail=detail,
        utilisateur=utilisateur,
    )
