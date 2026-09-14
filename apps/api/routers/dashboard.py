"""
Vue d'ensemble : KPI, priorites, sante de la surveillance et parcours de
mise en route.

Tous les chiffres sont calcules sur le **perimetre du client** (ce qui matche
un actif declare), jamais sur toute la BDP — sinon ils se gonflent avec des
renseignements portant sur des produits qu'il ne possede pas.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.utils import timezone
from ninja import Router

from apps.api.schemas import DashboardOut
from apps.api.serializers import paliers_par_renseignement, renseignement_out
from apps.bdc.models import ActifClient, RenseignementConsulte, Traitement
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching, calculer_perimetre_stats

router = Router()

_ORDRE_CRITICITE = {"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}
_OUVERTS = ("a_traiter", "en_cours")


@router.get("", response=DashboardOut)
def vue_ensemble(request):
    aujourdhui = timezone.localdate()
    resultats = calculer_matching()
    paliers = paliers_par_renseignement(resultats)
    # Seule source des chiffres agreges (voir apps/matching/services.py) : ne
    # jamais recalculer par_criticite/par_etape/nb_* localement ici.
    stats = calculer_perimetre_stats()

    tous = list(Renseignement.objects.all())
    traitements = {t.id_renseignement_bdp: t for t in Traitement.objects.select_related("actif")}
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))

    pertinents = list({r.renseignement.id_renseignement_bdp: r.renseignement for r in resultats}.values())

    def statut_de(r):
        return getattr(traitements.get(r.id_renseignement_bdp), "statut", "a_traiter")

    ouverts = [r for r in pertinents if statut_de(r) in _OUVERTS]
    non_consultes = [r for r in pertinents if r.id_renseignement_bdp not in consultes]

    # --- Sante de la surveillance ---
    couverts = {r.actif.pk for r in resultats}
    sans_renseignement = [a for a in ActifClient.objects.all() if a.pk not in couverts]
    sante = [
        {
            "niveau": "warn",
            "titre": f"{a} non couvert",
            "detail": "Aucune source ne le surveille — ce n'est pas une garantie d'absence de vulnérabilité.",
        }
        for a in sans_renseignement
    ]
    if not sans_renseignement:
        sante.append(
            {
                "niveau": "ok",
                "titre": "Tous vos actifs sont couverts",
                "detail": "Au moins une source les surveille activement.",
            }
        )
    sante.append(
        {"niveau": "ok", "titre": "4 sources interrogées", "detail": "NVD, CERT-FR, CNIL, endoflife.date"}
    )

    # --- Delais de cloture ---
    total_traitements = Traitement.objects.count()
    clos = Traitement.objects.filter(statut="clos").count()
    taux_cloture = round(100 * clos / total_traitements) if total_traitements else None

    delais = []
    for t in Traitement.objects.filter(statut="clos").prefetch_related("historique"):
        evenements = {h.evenement: h.horodatage for h in t.historique.all()}
        debut, fin = evenements.get("Découvert"), evenements.get("Clos")
        if debut and fin:
            delais.append((fin - debut).total_seconds() / 86400)
    delai_moyen = round(sum(delais) / len(delais), 1) if delais else None

    # --- Echeances ---
    echeances = [
        {
            "id_renseignement": t.id_renseignement_bdp,
            "actif": str(t.actif) if t.actif else "—",
            "titre": next(
                (r.titre for r in tous if r.id_renseignement_bdp == t.id_renseignement_bdp),
                "Renseignement retiré",
            ),
            "echeance": t.echeance,
        }
        for t in Traitement.objects.select_related("actif")
        .filter(echeance__gte=aujourdhui, echeance__lt=aujourdhui + timedelta(days=7), statut__in=_OUVERTS)
        .order_by("echeance")[:5]
    ]
    nb_en_retard = Traitement.objects.filter(echeance__lt=aujourdhui, statut__in=_OUVERTS).count()

    # --- Activite de collecte, 6 dernieres semaines ---
    activite = []
    for i in range(5, -1, -1):
        debut = aujourdhui - timedelta(days=aujourdhui.weekday() + 7 * i)
        n = sum(1 for r in tous if debut <= r.decouvert_le.date() < debut + timedelta(days=7))
        activite.append({"label": f"S-{i}" if i else "S", "n": n})
    activite_max = max((a["n"] for a in activite), default=0) or 1

    # --- Parcours de mise en route ---
    nb_technique = ActifClient.objects.filter(type="technique").count()
    nb_referentiels = ActifClient.objects.filter(type="normatif").count()
    a_traite = Traitement.objects.exclude(statut="a_traiter").exists()
    onboarding = [
        {"cle": "actifs", "fait": bool(nb_technique)},
        {"cle": "referentiels", "fait": bool(nb_referentiels)},
        {"cle": "traitement", "fait": a_traite},
    ]

    prioritaires = sorted(
        ouverts, key=lambda r: (_ORDRE_CRITICITE.get(r.criticite, 9), -r.decouvert_le.timestamp())
    )[:6]
    derniers = sorted(pertinents, key=lambda r: r.decouvert_le, reverse=True)[:6]

    return {
        "nb_renseignements": stats.nb_renseignements,
        "nb_ouverts": stats.nb_ouverts,
        "nb_actifs": stats.nb_actifs,
        "nb_actifs_technique": nb_technique,
        "nb_actifs_clean": stats.nb_actifs_clean,
        "nb_actifs_avec_non_traites": stats.nb_actifs_avec_non_traites,
        "nb_referentiels": nb_referentiels,
        "derniere_collecte": max((r.cree_le for r in tous), default=None),
        "par_criticite": stats.par_criticite,
        "par_criticite_ouverts": stats.par_criticite_ouverts,
        "par_etape": stats.par_etape,
        "nb_non_consultes": len(non_consultes),
        "nb_en_retard": nb_en_retard,
        "taux_cloture": taux_cloture,
        "delai_moyen_jours": delai_moyen,
        "prioritaires": [
            renseignement_out(r, consulte=r.id_renseignement_bdp in consultes) for r in prioritaires
        ],
        "derniers": [
            renseignement_out(r, consulte=r.id_renseignement_bdp in consultes) for r in derniers
        ],
        "echeances": echeances,
        "sante": sante,
        "activite": activite,
        "activite_max": activite_max,
        "onboarding": onboarding,
        "onboarding_termine": all(e["fait"] for e in onboarding),
    }
