"""
Renseignements filtres sur les actifs declares (via le Matching), et flux
complet de la BDP pour Actualites.

Le Matching reste en lecture seule : ce routeur ne lui fait jamais rien
ecrire, il se contente de consommer ses resultats.
"""

from __future__ import annotations

import re
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.api.schemas import (
    MessageOut,
    RenseignementDetail,
    RenseignementOut,
    RenseignementsListe,
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
from apps.matching.services import calculer_matching, calculer_perimetre_stats

router = Router()

# Une reference de vulnerabilite : CVE-2024-1234, GHSA-xxxx, DSA-1234-1…
# Sert a n'elargir la recherche au champ `reference_externe` que dans ce cas.
MOTIF_REFERENCE = re.compile(r"^(cve|ghsa|dsa|dla|usn|certfr)[-\s]", re.IGNORECASE)

_ORDRE_CRITICITE = {"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}
_ORDRE_STATUT = {"a_traiter": 0, "en_cours": 1, "clos": 2, "non_applicable": 3}


@router.get("", response=RenseignementsListe)
def lister(
    request,
    actif: int | None = Query(None),
    type: str | None = Query(None),
    criticite: str | None = Query(None),
    statut: str | None = Query(None),
    q: str | None = Query(None),
    tri: str = Query("date"),
):
    """Feed filtre sur le perimetre du client.

    Un seul passage de Matching : il etait relance a chaque besoin dans les
    anciennes vues, alors qu'il parcourt la BDP.

    `stats` est calcule sur le perimetre choisi (l'actif selectionne, ou tout
    le client) AVANT tout filtre d'affichage (criticite/statut/q) : filtrer
    la liste ne doit jamais faire bouger les chiffres affiches a cote — c'est
    le contrat que ce endpoint garantit desormais explicitement.
    """
    resultats = calculer_matching()
    paliers = paliers_par_renseignement(resultats)
    stats = calculer_perimetre_stats(actif_id=actif)

    if actif is not None:
        items = [r.renseignement for r in resultats if r.actif.pk == actif]
    else:
        items = list({r.renseignement.id_renseignement_bdp: r.renseignement for r in resultats}.values())
        if type in ("technique", "normatif"):
            items = [r for r in items if r.type == type]

    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))
    nb_non_consultes = sum(1 for r in items if r.id_renseignement_bdp not in consultes)

    if criticite in dict(Renseignement.CRITICITE_CHOICES):
        items = [r for r in items if r.criticite == criticite]

    traitements = {t.id_renseignement_bdp: t for t in Traitement.objects.select_related("actif")}

    if statut:
        statuts_voulus = {s.strip() for s in statut.split(",") if s.strip()}
        items = [
            r
            for r in items
            if getattr(traitements.get(r.id_renseignement_bdp), "statut", "a_traiter") in statuts_voulus
        ]

    if q:
        terme = q.lower()
        items = [
            r
            for r in items
            if terme in r.titre.lower()
            or terme in r.description.lower()
            or terme in r.reference_courte.lower()
        ]

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
    return {
        "items": sortie,
        "stats": {
            "nb_renseignements": stats.nb_renseignements,
            "nb_ouverts": stats.nb_ouverts,
            "par_etape": stats.par_etape,
            "par_criticite_ouverts": stats.par_criticite_ouverts,
            "nb_non_consultes": nb_non_consultes,
        },
    }


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

        # Recherche volontairement restreinte au titre.
        #
        # Chercher aussi dans `description` remontait des resultats hors sujet
        # (« kubernetes » sortait une faille MLRun dont le paragraphe mentionne
        # Kubernetes en passant) et imposait un parcours complet de la table :
        # seul `titre` porte un index trigram.
        #
        # Le "OU" est le piege a connaitre : un seul champ non indexe dedans
        # et PostgreSQL abandonne TOUS les index de la clause. On isole donc
        # `reference_externe` (non indexe) dans une branche a part, empruntee
        # uniquement quand le terme ressemble vraiment a une reference de
        # vulnerabilite — cas rare et volontaire. Le cas courant reste sur le
        # seul index du titre.
        if MOTIF_REFERENCE.match(q):
            qs = qs.filter(Q(reference_externe__icontains=q) | Q(titre__icontains=q))
        else:
            qs = qs.filter(titre__icontains=q)

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
