"""
Renseignements filtres sur les actifs declares (via le Matching), et flux
complet de la BDP pour Actualites.

Le Matching reste en lecture seule : ce routeur ne lui fait jamais rien
ecrire, il se contente de consommer ses resultats.
"""

from __future__ import annotations

from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.api.schemas import (
    MessageOut,
    RenseignementDetail,
    RenseignementListItem,
    RenseignementOut,
)
from apps.api.serializers import (
    cvss_axes,
    match_info,
    paliers_par_renseignement,
    renseignement_out,
    traitement_bref,
    traitement_detail,
)
from apps.bdc.models import ActifClient, RenseignementConsulte, Traitement
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

router = Router()

_ORDRE_CRITICITE = {"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}
_ORDRE_STATUT = {"a_traiter": 0, "en_cours": 1, "clos": 2, "non_applicable": 3}


@router.get("", response=list[RenseignementListItem])
def lister(
    request,
    actif: int | None = Query(None),
    type: str | None = Query(None),
    criticite: str | None = Query(None),
    tri: str = Query("date"),
):
    """Feed filtre sur le perimetre du client.

    Un seul passage de Matching : il etait relance a chaque besoin dans les
    anciennes vues, alors qu'il parcourt la BDP.
    """
    resultats = calculer_matching()
    paliers = paliers_par_renseignement(resultats)

    if actif is not None:
        items = [r.renseignement for r in resultats if r.actif.pk == actif]
    else:
        items = list({r.renseignement.id_renseignement_bdp: r.renseignement for r in resultats}.values())
        if type in ("technique", "normatif"):
            items = [r for r in items if r.type == type]

    if criticite in dict(Renseignement.CRITICITE_CHOICES):
        items = [r for r in items if r.criticite == criticite]

    traitements = {t.id_renseignement_bdp: t for t in Traitement.objects.select_related("actif")}
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))

    if tri == "criticite":
        items.sort(key=lambda r: (_ORDRE_CRITICITE.get(r.criticite, 9), -r.decouvert_le.timestamp()))
    elif tri == "statut":
        items.sort(
            key=lambda r: (
                _ORDRE_STATUT.get(getattr(traitements.get(r.id_renseignement_bdp), "statut", "a_traiter"), 9),
                -r.decouvert_le.timestamp(),
            )
        )
    else:
        items.sort(key=lambda r: r.decouvert_le, reverse=True)

    sortie = []
    for r in items:
        t = traitements.get(r.id_renseignement_bdp)
        sortie.append(
            {
                "renseignement": renseignement_out(r, consulte=r.id_renseignement_bdp in consultes),
                "traitement": traitement_bref(t) if t else None,
                "match": match_info(paliers.get(r.id_renseignement_bdp)),
            }
        )
    return sortie


@router.get("/actualites", response=list[RenseignementOut])
def actualites(
    request,
    q: str | None = Query(None),
    type: str | None = Query(None),
    limite: int = Query(100, le=500),
):
    """Flux brut de la BDP, volontairement NON filtre sur les actifs du
    client (brief : montrer la valeur de la base au-dela de son perimetre)."""
    qs = Renseignement.objects.all()
    if type in ("technique", "normatif"):
        qs = qs.filter(type=type)
    if q:
        from django.db.models import Q

        qs = qs.filter(Q(titre__icontains=q) | Q(source__icontains=q) | Q(description__icontains=q))

    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))
    return [
        renseignement_out(r, consulte=r.id_renseignement_bdp in consultes)
        for r in qs.order_by("-decouvert_le")[:limite]
    ]


@router.get("/{uuid:id_renseignement}", response=RenseignementDetail)
def detail(request, id_renseignement: UUID):
    r = get_object_or_404(Renseignement, id_renseignement_bdp=id_renseignement)
    t = Traitement.objects.filter(id_renseignement_bdp=id_renseignement).select_related("actif").first()
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))
    paliers = paliers_par_renseignement(calculer_matching())

    return {
        "renseignement": renseignement_out(r, consulte=id_renseignement in consultes),
        "traitement": traitement_detail(t) if t else None,
        "match": match_info(paliers.get(id_renseignement)),
        "cvss_axes": cvss_axes(r),
    }


@router.post("/{uuid:id_renseignement}/consulter", response=MessageOut)
def marquer_consulte(request, id_renseignement: UUID):
    RenseignementConsulte.objects.get_or_create(id_renseignement_bdp=id_renseignement)
    return {"detail": "ok"}


@router.get("/actifs/liste", response=list[dict])
def actifs_du_feed(request, tri: str = Query("az")):
    """Colonne laterale du feed : les actifs, avec leur nombre de
    renseignements et de critiques, pour pouvoir trier dessus."""
    from collections import Counter

    resultats = calculer_matching()
    par_actif = Counter()
    crit_par_actif = Counter()
    for r in resultats:
        par_actif[r.actif.pk] += 1
        if r.renseignement.criticite == "critique":
            crit_par_actif[r.actif.pk] += 1

    actifs = list(ActifClient.objects.all())
    if tri == "nb":
        actifs.sort(key=lambda a: -par_actif.get(a.pk, 0))
    elif tri == "critique":
        actifs.sort(key=lambda a: (-crit_par_actif.get(a.pk, 0), str(a)))
    else:
        actifs.sort(key=lambda a: str(a))

    return [
        {
            "id": a.pk,
            "type": a.type,
            "libelle": str(a),
            "version": a.version,
            "nb": par_actif.get(a.pk, 0),
            "nb_critiques": crit_par_actif.get(a.pk, 0),
        }
        for a in actifs
    ]
