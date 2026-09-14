"""
Journal unifie des actions du client (panneau "Historique des actions" de
Renseignements) : lecture seule sur ActionHistorique, alimente par
apps.api.journal.consigner() a chaque site de mutation (actifs.py,
traitement.py).
"""

from __future__ import annotations

from ninja import Query, Router

from apps.api.schemas import ActionHistoriqueOut
from apps.bdc.models import ActionHistorique

router = Router()


@router.get("", response=list[ActionHistoriqueOut])
def lister(
    request,
    type: str | None = Query(None),
    decalage: int = Query(0),
    limite: int = Query(30, le=100),
):
    qs = ActionHistorique.objects.all()
    if type in dict(ActionHistorique.TYPE_OBJET_CHOICES):
        qs = qs.filter(type_objet=type)

    return [
        {
            "id": a.pk,
            "type_objet": a.type_objet,
            "type_objet_label": a.get_type_objet_display(),
            "action": a.action,
            "action_label": a.get_action_display(),
            "objet_repr": a.objet_repr,
            "detail": a.detail,
            "utilisateur": a.utilisateur,
            "horodatage": a.horodatage,
        }
        for a in qs[decalage : decalage + limite]
    ]
