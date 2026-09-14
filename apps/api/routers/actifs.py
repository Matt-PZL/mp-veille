"""
Inventaire des actifs et referentiels declares par le client, plus le
catalogue de reference qui aide a la saisie.

Toute modification d'actif journalise un HistoriqueActif : c'est la trace
qui permet de repondre a un auditeur sur l'evolution du perimetre.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.api.schemas import (
    ActifCreate,
    ActifOut,
    ActifVersionUpdate,
    HistoriqueActifOut,
    MessageOut,
    ProduitCatalogue,
)
from apps.api.serializers import actif_out
from apps.bdc.models import ActifClient, HistoriqueActif, Traitement
from apps.matching.services import calculer_matching

router = Router()


def _pks_couverts() -> set[int]:
    """Actifs pour lesquels au moins une source remonte quelque chose.

    « Non couvert » ne veut pas dire « sain » : seulement qu'aucune collecte
    ne le surveille aujourd'hui. Le libelle cote front doit le dire.
    """
    return {r.actif.pk for r in calculer_matching()}


@router.get("", response=list[ActifOut])
def lister(request, q: str | None = Query(None), type: str | None = Query(None)):
    qs = ActifClient.objects.all()
    if type in ("technique", "normatif"):
        qs = qs.filter(type=type)

    actifs = sorted(qs, key=lambda a: str(a))
    if q:
        terme = q.lower()
        actifs = [a for a in actifs if terme in str(a).lower() or terme in a.editeur.lower()]

    couverts = _pks_couverts()
    return [actif_out(a, couvert=a.pk in couverts) for a in actifs]


@router.get("/stats", response=dict)
def stats(request):
    couverts = _pks_couverts()
    total = ActifClient.objects.count()
    return {
        "total": total,
        "technique": ActifClient.objects.filter(type="technique").count(),
        "normatif": ActifClient.objects.filter(type="normatif").count(),
        "non_couverts": total - len(couverts),
    }


@router.post("", response={200: ActifOut, 422: dict})
def creer(request, donnees: ActifCreate):
    if donnees.type not in ("technique", "normatif"):
        return 422, {"erreurs": {"type": "Type invalide."}}
    if donnees.type == "technique" and not donnees.produit.strip():
        return 422, {"erreurs": {"produit": "Le produit est obligatoire pour un actif technique."}}
    if donnees.type == "normatif" and not donnees.referentiel.strip():
        return 422, {"erreurs": {"referentiel": "Le référentiel est obligatoire."}}

    actif = ActifClient.objects.create(
        type=donnees.type,
        categorie=donnees.categorie,
        editeur=donnees.editeur,
        produit=donnees.produit,
        version=donnees.version,
        referentiel=donnees.referentiel,
    )
    HistoriqueActif.objects.create(
        actif_repr=str(actif),
        evenement="ajout",
        detail=f"Version {actif.version}" if actif.version else "",
    )
    return 200, actif_out(actif, couvert=actif.pk in _pks_couverts())


@router.put("/{int:pk}/version", response=ActifOut)
def monter_version(request, pk: int, donnees: ActifVersionUpdate):
    actif = get_object_or_404(ActifClient, pk=pk)
    ancienne = actif.version
    actif.version = donnees.version
    actif.save()
    HistoriqueActif.objects.create(
        actif_repr=str(actif),
        evenement="version",
        detail=f"{ancienne or '—'} → {actif.version or '—'}",
    )
    return actif_out(actif, couvert=actif.pk in _pks_couverts())


@router.delete("/{int:pk}", response=MessageOut)
def retirer(request, pk: int, purger: bool = Query(False)):
    """Retire un actif. `purger` decide du sort de son historique de
    traitement — le brief impose que ce soit un choix explicite du client,
    jamais un effet de bord silencieux."""
    actif = get_object_or_404(ActifClient, pk=pk)
    repr_actif = str(actif)

    if purger:
        Traitement.objects.filter(actif=actif).delete()
    else:
        # SET_NULL cote modele : les traitements survivent, detaches.
        Traitement.objects.filter(actif=actif).update(actif=None)

    actif.delete()
    HistoriqueActif.objects.create(
        actif_repr=repr_actif,
        evenement="suppression_purge" if purger else "suppression_conserve",
        detail="Historique purgé" if purger else "Historique conservé",
    )
    return {"detail": f"{repr_actif} retiré."}


@router.get("/historique", response=list[HistoriqueActifOut])
def historique(request, limite: int = Query(30, le=200)):
    return [
        {
            "id": h.pk,
            "actif_repr": h.actif_repr,
            "evenement": h.evenement,
            "evenement_label": h.get_evenement_display(),
            "detail": h.detail,
            "horodatage": h.horodatage,
        }
        for h in HistoriqueActif.objects.all()[:limite]
    ]


@router.get("/catalogue", response=list[ProduitCatalogue])
def catalogue(request, q: str | None = Query(None), limite: int = Query(40, le=200)):
    """Recherche « tape et trouve » dans le catalogue de reference
    (~470 produits alimentes par endoflife.date)."""
    from apps.catalogue.models import ActifCatalogueProduit

    qs = ActifCatalogueProduit.objects.prefetch_related("versions")
    if q:
        from django.db.models import Q

        qs = qs.filter(Q(produit__icontains=q) | Q(editeur__icontains=q) | Q(categorie__icontains=q))

    return [
        {
            "categorie": p.categorie,
            "editeur": p.editeur,
            "produit": p.produit,
            "versions": [v.version for v in p.versions.all()[:40]],
        }
        for p in qs[:limite]
    ]


@router.get("/referentiels", response=list[str])
def referentiels(request):
    from apps.api.taxonomie import REFERENTIELS_NORMATIFS

    return list(REFERENTIELS_NORMATIFS)
