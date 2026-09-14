"""
Traitement des renseignements — l'ecran qui sert de preuve d'audit.

Les regles de validation sont identiques a celles des anciennes vues et
restent appliquees **cote serveur** : un statut "Démarré" sans plan d'action
ou un "Clos" sans justificatif est refuse ici, pas seulement grise dans
l'interface.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Query, Router
from ninja.files import UploadedFile

from apps.api.schemas import MessageOut, TraitementDetail, TraitementListItem, TraitementWrite
from apps.api.serializers import renseignement_out, traitement_detail
from apps.bdc.models import HistoriqueTraitement, Traitement
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

router = Router()

_ORDRE_CRITICITE = {"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}
_OUVERTS = ("a_traiter", "en_cours")


def _actif_pour(id_renseignement: UUID):
    """Rattache un traitement au bon actif via le Matching (lecture seule)."""
    for resultat in calculer_matching():
        if resultat.renseignement.id_renseignement_bdp == id_renseignement:
            return resultat.actif
    return None


def _valider(donnees: TraitementWrite) -> dict[str, str]:
    erreurs: dict[str, str] = {}
    if donnees.statut not in dict(Traitement.STATUT_CHOICES):
        erreurs["statut"] = "Choisissez un statut valide."
        return erreurs

    if donnees.statut == "en_cours":
        if not donnees.plan_action.strip():
            erreurs["plan_action"] = "Le plan d'action est obligatoire pour démarrer le traitement."
        if donnees.echeance is None:
            erreurs["echeance"] = "La date prévisionnelle est obligatoire."
        if donnees.passage_cab is None:
            erreurs["passage_cab"] = "Précisez si un passage en CAB est nécessaire."
    elif donnees.statut in ("clos", "non_applicable"):
        if not donnees.justificatif.strip():
            erreurs["justificatif"] = "Un justificatif est obligatoire pour clore ou marquer non applicable."
    return erreurs


@router.get("", response=list[TraitementListItem])
def lister(
    request,
    statut: str | None = Query(None),
    criticite: str | None = Query(None),
    q: str | None = Query(None),
    date_debut: date | None = Query(None),
    date_fin: date | None = Query(None),
    tri: str = Query("recent"),
):
    qs = Traitement.objects.select_related("actif").prefetch_related("historique")

    if statut == "en_retard":
        from django.utils import timezone

        qs = qs.filter(echeance__lt=timezone.localdate(), statut__in=_OUVERTS)
    elif statut in dict(Traitement.STATUT_CHOICES):
        qs = qs.filter(statut=statut)

    if date_debut:
        qs = qs.filter(maj_le__date__gte=date_debut)
    if date_fin:
        qs = qs.filter(maj_le__date__lte=date_fin)

    traitements = list(qs)
    renseignements = {r.id_renseignement_bdp: r for r in Renseignement.objects.all()}

    if q:
        terme = q.lower()

        def correspond(t):
            r = renseignements.get(t.id_renseignement_bdp)
            cible = f"{t.actif or ''} {r.titre if r else ''} {r.reference_courte if r else ''}".lower()
            return terme in cible

        traitements = [t for t in traitements if correspond(t)]

    if criticite:
        traitements = [
            t
            for t in traitements
            if (r := renseignements.get(t.id_renseignement_bdp)) and r.criticite == criticite
        ]

    if tri == "criticite":
        traitements.sort(
            key=lambda t: _ORDRE_CRITICITE.get(
                getattr(renseignements.get(t.id_renseignement_bdp), "criticite", ""), 9
            )
        )
    elif tri == "echeance":
        # Sans echeance = en dernier, sinon la plus proche d'abord.
        traitements.sort(key=lambda t: (t.echeance is None, t.echeance or date.max))
    else:
        traitements.sort(key=lambda t: t.maj_le, reverse=True)

    return [
        {
            "traitement": traitement_detail(t),
            "renseignement": renseignement_out(r) if (r := renseignements.get(t.id_renseignement_bdp)) else None,
        }
        for t in traitements
    ]


@router.get("/compteurs", response=dict)
def compteurs(request):
    from django.utils import timezone

    base = {code: 0 for code, _ in Traitement.STATUT_CHOICES}
    for t in Traitement.objects.all():
        base[t.statut] = base.get(t.statut, 0) + 1
    return {
        **base,
        "total": Traitement.objects.count(),
        "en_retard": Traitement.objects.filter(
            echeance__lt=timezone.localdate(), statut__in=_OUVERTS
        ).count(),
    }


# POST et non PUT : la requete est multipart (preuve fichier a la cloture),
# or Django ne peuple request.FILES que sur POST — django-ninja refuse donc
# un PUT multipart sans middleware de compatibilite.
@router.post(
    "/renseignement/{uuid:id_renseignement}",
    response={200: TraitementDetail, 422: dict},
)
def ecrire(
    request,
    id_renseignement: UUID,
    donnees: Form[TraitementWrite],
    preuve_fichier: UploadedFile | None = File(None),
):
    """Cree ou met a jour le traitement d'un renseignement.

    En multipart (et non JSON) parce que la cloture accepte une preuve
    fichier — le front envoie un FormData.
    """
    get_object_or_404(Renseignement, id_renseignement_bdp=id_renseignement)

    erreurs = _valider(donnees)
    if erreurs:
        return 422, {"erreurs": erreurs}

    t = Traitement.objects.filter(id_renseignement_bdp=id_renseignement).first()
    creation = t is None
    if creation:
        t = Traitement(
            id_renseignement_bdp=id_renseignement,
            actif=_actif_pour(id_renseignement),
        )
    ancien_statut = None if creation else t.statut

    t.statut = donnees.statut
    if donnees.justificatif:
        t.justificatif = donnees.justificatif
    if donnees.statut == "en_cours":
        t.plan_action = donnees.plan_action
        t.echeance = donnees.echeance
        t.passage_cab = donnees.passage_cab
    if preuve_fichier:
        t.preuve_fichier = preuve_fichier
    t.save()

    # Mini-timeline : decouverte -> prise en charge -> cloture.
    if creation:
        HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
        if donnees.statut != "a_traiter":
            HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())
    elif ancien_statut != donnees.statut:
        HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())

    t.refresh_from_db()
    return 200, traitement_detail(t)


@router.get("/{int:pk}/pdf", response=None)
def export_pdf(request, pk: int):
    """Delegue au generateur de apps/api/pdf.py."""
    from apps.api.pdf import export_traitement_pdf

    reponse: HttpResponse = export_traitement_pdf(request, pk)
    return reponse


@router.delete("/{int:pk}", response=MessageOut)
def supprimer(request, pk: int):
    Traitement.objects.filter(pk=pk).delete()
    return {"detail": "Traitement supprimé."}
