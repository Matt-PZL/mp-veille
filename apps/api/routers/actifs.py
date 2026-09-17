"""
Inventaire des actifs et referentiels declares par le client, plus le
catalogue de reference qui aide a la saisie.

Toute modification d'actif journalise un HistoriqueActif : c'est la trace
qui permet de repondre a un auditeur sur l'evolution du perimetre.
"""

from __future__ import annotations

import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router

from apps.api.schemas import (
    ActifCreate,
    ActifOut,
    ActifVersionUpdate,
    HistoriqueActifOut,
    MessageOut,
    ProduitCatalogue,
)
from apps.api.journal import consigner
from apps.api.serializers import actif_out
from apps.bdc.models import ActifClient, HistoriqueActif, Traitement
from apps.matching.services import actifs_avec_renseignements_ouverts, calculer_matching

router = Router()


def _nom_fichier(extension: str) -> str:
    """Date dans le nom : deux exports du meme inventaire a des jours
    differents ne doivent pas se marcher dessus dans un dossier."""
    return f"actifs-{timezone.localdate():%Y-%m-%d}.{extension}"


def _cle_unicite(type_actif: str, libelle: str, version: str) -> tuple[str, str, str]:
    """Identite visible d'un actif dans l'inventaire.

    Deux lignes qui partagent cette cle s'affichent a l'identique a l'ecran :
    c'est exactement ce qu'on veut interdire. La casse et les espaces de bord
    sont neutralises, sinon « Kubernetes » et « kubernetes  » passeraient pour
    deux actifs distincts alors qu'ils se ressemblent trait pour trait.

    La version fait partie de la cle : deux Kubernetes restent legitimes tant
    qu'ils portent des versions differentes — c'est le cas d'usage normal
    d'un parc ou plusieurs versions cohabitent.
    """
    return (
        type_actif,
        " ".join(libelle.lower().split()),
        " ".join(version.lower().split()),
    )


def _doublon(
    type_actif: str, libelle: str, version: str, *, sauf_pk: int | None = None
) -> ActifClient | None:
    """Actif deja declare portant la meme identite visible, s'il existe.

    Compare en Python sur `str(actif)` plutot qu'en SQL : c'est ce libelle-la
    que l'utilisateur voit dans la liste, et il se derive de plusieurs champs
    selon le type. L'inventaire d'un client se compte en dizaines de lignes,
    le cout est negligeable.
    """
    cle = _cle_unicite(type_actif, libelle, version)
    for a in ActifClient.objects.filter(type=type_actif):
        if a.pk != sauf_pk and _cle_unicite(a.type, str(a), a.version) == cle:
            return a
    return None


def _pks_couverts() -> set[int]:
    """Actifs pour lesquels au moins une source remonte quelque chose.

    « Non couvert » ne veut pas dire « sain » : seulement qu'aucune collecte
    ne le surveille aujourd'hui. Le libelle cote front doit le dire.
    """
    return {r.actif.pk for r in calculer_matching()}


def filtrer_actifs(
    q: str | None = None,
    type: str | None = None,
    etat: str | None = None,
) -> list[ActifClient]:
    """Selection commune a la liste et aux exports.

    Les exports doivent rendre exactement les lignes affichees a l'ecran :
    un filtre duplique finirait par deriver, et un PDF qui ne correspond pas
    a ce que le client voyait n'a aucune valeur d'audit.

    `etat=clean` / `etat=non_traite` partitionne sur le meme calcul que les
    tuiles Actifs clean / Actifs avec renseignements non traites de Vue
    d'ensemble (apps.matching.services.actifs_avec_renseignements_ouverts).
    """
    qs = ActifClient.objects.all()
    if type in ("technique", "normatif"):
        qs = qs.filter(type=type)

    if etat in ("clean", "non_traite"):
        ouverts = actifs_avec_renseignements_ouverts()
        qs = qs.exclude(pk__in=ouverts) if etat == "clean" else qs.filter(pk__in=ouverts)

    actifs = sorted(qs, key=lambda a: str(a))
    if q:
        terme = q.lower()
        actifs = [a for a in actifs if terme in str(a).lower() or terme in a.editeur.lower()]
    return actifs


@router.get("", response=list[ActifOut])
def lister(
    request,
    q: str | None = Query(None),
    type: str | None = Query(None),
    etat: str | None = Query(None),
):
    actifs = filtrer_actifs(q, type, etat)
    couverts = _pks_couverts()
    return [actif_out(a, couvert=a.pk in couverts) for a in actifs]


@router.get("/export/csv", response=None)
def export_csv(
    request,
    q: str | None = Query(None),
    type: str | None = Query(None),
    etat: str | None = Query(None),
):
    """Inventaire filtre au format CSV.

    Le fichier s'ouvre en Excel : separateur « ; » (Excel francais l'attend)
    et BOM en tete, sans quoi Excel lit le fichier en latin-1 et abime tous
    les accents (« Référentiel » -> « RÃ©fÃ©rentiel »).

    Le BOM est ecrit une seule fois, a la main. Declarer charset=utf-8-sig
    sur la reponse ne marche pas : Django encode alors *chaque* write() avec
    ce codec, et le BOM se retrouve reproduit devant chaque ligne.
    """
    actifs = filtrer_actifs(q, type, etat)
    couverts = _pks_couverts()

    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{_nom_fichier("csv")}"'
    reponse.write("\ufeff")

    colonnes = csv.writer(reponse, delimiter=";")
    colonnes.writerow(
        ["Type", "Categorie", "Editeur", "Produit / Referentiel", "Version", "Couverture", "Declare le"]
    )
    for a in actifs:
        colonnes.writerow(
            [
                a.get_type_display(),
                a.categorie,
                a.editeur,
                str(a),
                a.version,
                "Couvert" if a.pk in couverts else "Non couvert",
                a.ajoute_le.strftime("%d/%m/%Y"),
            ]
        )
    return reponse


@router.get("/export/pdf", response=None)
def export_pdf(
    request,
    q: str | None = Query(None),
    type: str | None = Query(None),
    etat: str | None = Query(None),
):
    """Inventaire filtre au format PDF — delegue a apps/api/pdf.py."""
    from apps.api.pdf import export_actifs_pdf

    actifs = filtrer_actifs(q, type, etat)
    return export_actifs_pdf(
        actifs,
        couverts=_pks_couverts(),
        filtres={"q": q, "type": type, "etat": etat},
        nom_fichier=_nom_fichier("pdf"),
    )


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

    # Un meme actif declare deux fois fausse tout ce qui compte derriere :
    # KPI d'inventaire, exports, et le matching qui remonterait deux fois le
    # meme renseignement.
    technique = donnees.type == "technique"
    libelle = (donnees.produit if technique else donnees.referentiel).strip()
    if _doublon(donnees.type, libelle, donnees.version):
        champ = "produit" if technique else "referentiel"
        if technique:
            version = donnees.version.strip()
            message = (
                f"« {libelle} » est déjà déclaré en version {version}."
                if version
                else f"« {libelle} » est déjà déclaré sans version."
            ) + " Pour suivre une autre version, indiquez un numéro différent."
        else:
            message = f"« {libelle} » est déjà déclaré."
        return 422, {"erreurs": {champ: message}}

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
    consigner(request, type_objet="actif", action="ajout", objet_repr=str(actif))
    return 200, actif_out(actif, couvert=actif.pk in _pks_couverts())


@router.put("/{int:pk}/version", response={200: ActifOut, 422: dict})
def monter_version(request, pk: int, donnees: ActifVersionUpdate):
    actif = get_object_or_404(ActifClient, pk=pk)
    ancienne = actif.version

    # Meme regle qu'a la creation : sans ce controle, ramener un actif sur la
    # version d'un autre recreerait par la bande le doublon interdit a l'ajout.
    if _doublon(actif.type, str(actif), donnees.version, sauf_pk=actif.pk):
        return 422, {
            "erreurs": {
                "version": (
                    f"« {actif} » est déjà déclaré en version {donnees.version.strip()}."
                    if donnees.version.strip()
                    else f"« {actif} » est déjà déclaré sans version."
                )
            }
        }

    actif.version = donnees.version
    actif.save()
    HistoriqueActif.objects.create(
        actif_repr=str(actif),
        evenement="version",
        detail=f"{ancienne or '—'} → {actif.version or '—'}",
    )
    consigner(
        request,
        type_objet="actif",
        action="modification",
        objet_repr=str(actif),
        detail=f"Version {ancienne or '—'} → {actif.version or '—'}",
    )
    return 200, actif_out(actif, couvert=actif.pk in _pks_couverts())


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
    consigner(
        request,
        type_objet="actif",
        action="suppression",
        objet_repr=repr_actif,
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
