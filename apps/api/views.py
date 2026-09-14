"""
Vues DRF — couche API pour le frontend Next.js (apps.api). Reutilise les
memes regles metier que apps.panel.views (perimetre "pertinent" scope aux
actifs declares, jamais toute la BDP brute) pour que les deux interfaces
(Django templates existants + Next.js) restent coherentes pendant la
migration progressive.
"""

from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.bdc.models import ActifClient, HistoriqueActif, RenseignementConsulte, Traitement
from apps.bdp.models import Renseignement
from apps.catalogue.models import ActifCatalogueProduit
from apps.matching.services import calculer_matching
from apps.vitrine.models import MessageContact

from .serializers import (
    ActifCatalogueProduitSerializer,
    ActifClientSerializer,
    HistoriqueActifSerializer,
    InscriptionSerializer,
    MessageContactSerializer,
    RenseignementSerializer,
    TraitementSerializer,
)

User = get_user_model()
_OUVERTS = ("a_traiter", "en_cours")


def _renseignements_pertinents():
    """Meme regle que apps.panel.views : uniquement ce qui matche un
    actif/referentiel reellement declare, pas toute la BDP brute."""
    return list(
        {r.renseignement.id_renseignement_bdp: r.renseignement for r in calculer_matching()}.values()
    )


class ContactThrottle(AnonRateThrottle):
    rate = "10/hour"


@api_view(["POST"])
@permission_classes([AllowAny])
def inscription(request):
    serializer = InscriptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    return Response(
        {"access": str(refresh.access_token), "refresh": str(refresh), "username": user.username},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def moi(request):
    return Response({"username": request.user.username, "email": request.user.email})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ContactThrottle])
def contact(request):
    serializer = MessageContactSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"ok": True}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    traitements_par_id = {t.id_renseignement_bdp: t for t in Traitement.objects.select_related("actif")}
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))
    aujourdhui = timezone.localdate()

    def statut_de(r):
        return getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter")

    pertinents = _renseignements_pertinents()
    ouverts = [r for r in pertinents if statut_de(r) in _OUVERTS]
    par_criticite = Counter(r.criticite or "moyenne" for r in ouverts)
    par_etape = Counter(statut_de(r) for r in pertinents)
    non_consultes = [r for r in pertinents if r.id_renseignement_bdp not in consultes]

    resultats_matching = calculer_matching()
    actifs_couverts = {r.actif for r in resultats_matching}
    actifs_sans_renseignement = [a for a in ActifClient.objects.all() if a not in actifs_couverts]

    total_traitements = Traitement.objects.count()
    clos_count = Traitement.objects.filter(statut="clos").count()
    taux_cloture = round(100 * clos_count / total_traitements) if total_traitements else None

    en_retard = list(
        Traitement.objects.select_related("actif")
        .filter(echeance__lt=aujourdhui, statut__in=_OUVERTS)
        .order_by("echeance")[:5]
    )
    echeances_a_venir = list(
        Traitement.objects.select_related("actif")
        .filter(echeance__gte=aujourdhui, echeance__lt=aujourdhui + timedelta(days=7), statut__in=_OUVERTS)
        .order_by("echeance")[:5]
    )
    renseignements_par_id = {r.id_renseignement_bdp: r for r in Renseignement.objects.all()}

    prioritaires = sorted(
        ouverts, key=lambda r: ({"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}.get(r.criticite, 9), -r.decouvert_le.timestamp())
    )[:5]
    derniers = sorted(pertinents, key=lambda r: r.decouvert_le, reverse=True)[:5]

    ctx = {"traitements_par_id": traitements_par_id}
    return Response({
        "nb_total_renseignements": len(pertinents),
        "nb_actifs": ActifClient.objects.count(),
        "par_criticite": dict(par_criticite),
        "par_etape": dict(par_etape),
        "non_consultes_count": len(non_consultes),
        "taux_cloture": taux_cloture,
        "total_traitements": total_traitements,
        "actifs_sans_renseignement": [str(a) for a in actifs_sans_renseignement],
        "en_retard": TraitementSerializer(en_retard, context={**ctx, "renseignements_par_id": renseignements_par_id}, many=True).data,
        "echeances_a_venir": TraitementSerializer(echeances_a_venir, context={**ctx, "renseignements_par_id": renseignements_par_id}, many=True).data,
        "prioritaires": RenseignementSerializer(prioritaires, context=ctx, many=True).data,
        "derniers_renseignements": RenseignementSerializer(derniers, context=ctx, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def renseignements_list(request):
    traitements_par_id = {t.id_renseignement_bdp: t for t in Traitement.objects.all()}
    actif_id = request.GET.get("actif")
    type_ = request.GET.get("type")
    criticite = request.GET.get("criticite")

    if actif_id:
        actif = ActifClient.objects.filter(pk=actif_id).first()
        items = [r.renseignement for r in calculer_matching(actifs=[actif] if actif else [])]
    else:
        items = _renseignements_pertinents()
        if type_ in ("technique", "normatif"):
            items = [r for r in items if r.type == type_]

    if criticite:
        items = [r for r in items if r.criticite == criticite]

    items.sort(key=lambda r: r.decouvert_le, reverse=True)
    data = RenseignementSerializer(items, context={"traitements_par_id": traitements_par_id}, many=True).data
    return Response({"count": len(data), "results": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def actifs_list(request):
    actifs = ActifClient.objects.all().order_by("categorie", "editeur", "produit")
    resultats_matching = calculer_matching()
    couverts_pks = {r.actif.pk for r in resultats_matching}
    data = ActifClientSerializer(actifs, many=True).data
    for row in data:
        row["couvert"] = row["id"] in couverts_pks
    historique = HistoriqueActif.objects.all()[:20]
    return Response({
        "count": len(data),
        "results": data,
        "historique": HistoriqueActifSerializer(historique, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogue_search(request):
    q = request.GET.get("q", "").strip()
    qs = ActifCatalogueProduit.objects.all()
    if q:
        qs = qs.filter(produit__icontains=q)[:30]
    else:
        qs = qs.none()
    return Response(ActifCatalogueProduitSerializer(qs, many=True).data)
