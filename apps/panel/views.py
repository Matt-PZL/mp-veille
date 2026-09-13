from collections import Counter
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bdc.models import (
    ActifClient,
    HistoriqueActif,
    HistoriqueTraitement,
    PreferenceNotification,
    RenseignementConsulte,
    Traitement,
)
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

_ORDRE_STATUT = {"a_traiter": 0, "en_cours": 1, "clos": 2, "non_applicable": 3}
_ORDRE_CRITICITE = {"critique": 0, "elevee": 1, "moyenne": 2, "faible": 3}
_OUVERTS = ("a_traiter", "en_cours")


def _actif_pour_renseignement(id_renseignement_bdp, resultats=None):
    """Retrouve l'actif client associe a un renseignement via le Matching
    (lecture seule) — sert a rattacher un Traitement au bon actif."""
    resultats = resultats if resultats is not None else calculer_matching()
    for resultat in resultats:
        if resultat.renseignement.id_renseignement_bdp == id_renseignement_bdp:
            return resultat.actif
    return None


@login_required
def vue_ensemble(request):
    """Tableau de bord : KPI et aperçu rapide, point d'entrée du panel."""
    traitements_par_id = {t.id_renseignement_bdp: t for t in Traitement.objects.select_related("actif")}
    tous_renseignements = list(Renseignement.objects.all())
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))
    aujourdhui = timezone.localdate()

    def statut_de(r):
        return getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter")

    # KPI/priorites du dashboard : uniquement ce qui concerne le client (matche
    # a un actif/referentiel declare), pas toute la BDP — sinon les chiffres
    # se gonflent avec des renseignements sur des produits qu'il ne possede
    # meme pas (meme principe que sur Renseignements, cf. calculer_matching).
    resultats_matching = calculer_matching()
    actifs_couverts = {r.actif for r in resultats_matching}
    actifs_sans_renseignement = [a for a in ActifClient.objects.all() if a not in actifs_couverts]
    renseignements_pertinents = list(
        {r.renseignement.id_renseignement_bdp: r.renseignement for r in resultats_matching}.values()
    )

    ouverts = [r for r in renseignements_pertinents if statut_de(r) in _OUVERTS]
    par_criticite = Counter(r.criticite or "moyenne" for r in ouverts)
    par_etape = Counter(statut_de(r) for r in renseignements_pertinents)
    non_consultes = [r for r in renseignements_pertinents if r.id_renseignement_bdp not in consultes]

    compteur_actifs = Counter()
    for t in traitements_par_id.values():
        if t.actif and t.statut in _OUVERTS:
            compteur_actifs[t.actif] += 1
    actifs_exposes = compteur_actifs.most_common(5)

    total_traitements = Traitement.objects.count()
    clos_count = Traitement.objects.filter(statut="clos").count()
    taux_cloture = round(100 * clos_count / total_traitements) if total_traitements else None

    delais = []
    for t in Traitement.objects.filter(statut="clos").prefetch_related("historique"):
        evenements = {h.evenement: h.horodatage for h in t.historique.all()}
        debut = evenements.get("Découvert")
        fin = evenements.get("Clos")
        if debut and fin:
            delais.append((fin - debut).total_seconds() / 86400)
    delai_moyen_jours = round(sum(delais) / len(delais), 1) if delais else None

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
    renseignements_par_id = {r.id_renseignement_bdp: r for r in tous_renseignements}

    prioritaires = sorted(
        ouverts,
        key=lambda r: (_ORDRE_CRITICITE.get(r.criticite, 9), -r.decouvert_le.timestamp()),
    )[:5]

    activite = []
    for i in range(5, -1, -1):
        debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday() + 7 * i)
        fin_semaine = debut_semaine + timedelta(days=7)
        n = sum(1 for r in tous_renseignements if debut_semaine <= r.decouvert_le.date() < fin_semaine)
        activite.append({"label": f"S-{i}" if i else "S", "n": n})
    activite_max = max((a["n"] for a in activite), default=0) or 1

    derniere_collecte = max((r.cree_le for r in tous_renseignements), default=None)
    derniers_renseignements_pertinents = sorted(
        renseignements_pertinents, key=lambda r: r.decouvert_le, reverse=True
    )[:5]

    return render(
        request,
        "panel/dashboard.html",
        {
            "par_criticite": par_criticite,
            "par_etape": par_etape,
            "actifs_exposes": actifs_exposes,
            "actifs_sans_renseignement": actifs_sans_renseignement,
            "taux_cloture": taux_cloture,
            "total_traitements": total_traitements,
            "delai_moyen_jours": delai_moyen_jours,
            "en_retard": en_retard,
            "echeances_a_venir": echeances_a_venir,
            "renseignements_par_id": renseignements_par_id,
            "derniers_renseignements": derniers_renseignements_pertinents,
            "prioritaires": prioritaires,
            "non_consultes": non_consultes,
            "activite": activite,
            "activite_max": activite_max,
            "derniere_collecte": derniere_collecte,
            "nb_ouverts": len(ouverts),
            "nb_total_renseignements": len(renseignements_pertinents),
            "nb_actifs": ActifClient.objects.count(),
        },
    )


@login_required
def renseignements(request):
    """01 · Renseignements sur les actifs — panneau Actifs (façon "Top
    repositories") à gauche, feed de renseignements au centre, derniers
    traitements à droite."""
    actifs = list(ActifClient.objects.all())

    q_actif = request.GET.get("q_actif", "").strip()
    if q_actif:
        actifs = [a for a in actifs if q_actif.lower() in str(a).lower()]

    tri_actifs = request.GET.get("tri_actifs", "az")
    if tri_actifs == "nb":
        actifs.sort(key=lambda a: a.traitements.count(), reverse=True)
    elif tri_actifs == "critique":
        # priorite aux actifs ayant le plus de renseignements critiques
        crit_par_actif = Counter()
        for r in calculer_matching():
            if r.renseignement.criticite == "critique":
                crit_par_actif[r.actif.pk] += 1
        actifs.sort(key=lambda a: (-crit_par_actif.get(a.pk, 0), str(a)))
    else:
        actifs.sort(key=lambda a: str(a))
    actifs_technique = [a for a in actifs if a.type == "technique"]
    actifs_normatif = [a for a in actifs if a.type == "normatif"]

    actif_selectionne = None
    actif_id = request.GET.get("actif")
    if actif_id:
        actif_selectionne = next((a for a in ActifClient.objects.all() if str(a.pk) == actif_id), None)

    type_selectionne = request.GET.get("type") if not actif_selectionne else None
    if type_selectionne not in ("technique", "normatif"):
        type_selectionne = None

    if actif_selectionne:
        items = [r.renseignement for r in calculer_matching(actifs=[actif_selectionne])]
    elif type_selectionne:
        items = list(Renseignement.objects.filter(type=type_selectionne))
    else:
        items = list(Renseignement.objects.all())

    traitements_par_id = {t.id_renseignement_bdp: t for t in Traitement.objects.all()}
    consultes = set(RenseignementConsulte.objects.values_list("id_renseignement_bdp", flat=True))

    criticite_filtre = request.GET.get("criticite")
    if criticite_filtre in dict(Renseignement.CRITICITE_CHOICES):
        items = [r for r in items if r.criticite == criticite_filtre]

    tri = request.GET.get("tri", "date")
    if tri == "statut":
        items.sort(key=lambda r: _ORDRE_STATUT.get(
            getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter"), 0
        ))
    elif tri == "criticite":
        items.sort(key=lambda r: _ORDRE_CRITICITE.get(r.criticite, 9))
    else:
        items.sort(key=lambda r: r.decouvert_le, reverse=True)

    renseignements_par_id = {r.id_renseignement_bdp: r for r in Renseignement.objects.all()}
    derniers_traitements = list(
        Traitement.objects.select_related("actif")
        .exclude(statut="a_traiter")
        .order_by("-maj_le")[:5]
    )

    import json

    from .taxonomie import REFERENTIELS_NORMATIFS, TAXONOMIE_TECHNIQUE

    # Stats de l'en-tete : uniquement ce qui concerne le client (matche a un
    # actif/referentiel declare), pas tout le flux BDP — la BDP contient des
    # milliers d'avis sur des produits que le client ne possede pas, compter
    # dessus donnerait des chiffres qui n'ont rien d'actionnable pour lui.
    renseignements_pertinents = {
        r.renseignement.id_renseignement_bdp: r.renseignement for r in calculer_matching()
    }.values()
    nb_nouveaux = sum(1 for r in renseignements_pertinents if r.id_renseignement_bdp not in consultes)
    nb_critiques = sum(1 for r in renseignements_pertinents if r.criticite == "critique")
    nb_a_traiter = sum(
        1 for r in renseignements_pertinents
        if getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter") == "a_traiter"
    )

    return render(
        request,
        "panel/renseignements.html",
        {
            "actifs_technique": actifs_technique,
            "actifs_normatif": actifs_normatif,
            "nb_actifs": len(actifs),
            "items": items,
            "traitements_par_id": traitements_par_id,
            "consultes": consultes,
            "actif_selectionne": actif_selectionne,
            "type_selectionne": type_selectionne,
            "criticite_filtre": criticite_filtre,
            "tri": tri,
            "tri_actifs": tri_actifs,
            "q_actif": q_actif,
            "derniers_traitements": derniers_traitements,
            "renseignements_par_id": renseignements_par_id,
            "taxonomie_json": json.dumps(TAXONOMIE_TECHNIQUE),
            "referentiels": REFERENTIELS_NORMATIFS,
            "nb_total_renseignements": len(renseignements_pertinents),
            "nb_nouveaux": nb_nouveaux,
            "nb_critiques": nb_critiques,
            "nb_a_traiter": nb_a_traiter,
        },
    )


@login_required
def marquer_consulte(request, id_renseignement_bdp):
    if request.method == "POST":
        RenseignementConsulte.objects.get_or_create(id_renseignement_bdp=id_renseignement_bdp)
    return JsonResponse({"ok": True})


@login_required
def traiter_renseignement(request, id_renseignement_bdp):
    """Page dediee de traitement d'un renseignement (brief : quelque chose
    de plus serieux que le choix rapide precedent).

    Le statut choisi impose des informations differentes, avec blocage reel
    cote serveur (pas seulement visuel) :
      - Démarré : plan d'action + date prévisionnelle + passage CAB obligatoires
      - Clos / Non applicable : justificatif obligatoire (preuve fichier optionnelle pour Clos)
    """
    renseignement = get_object_or_404(Renseignement, id_renseignement_bdp=id_renseignement_bdp)
    t = Traitement.objects.filter(id_renseignement_bdp=id_renseignement_bdp).first()
    erreurs = {}
    statut_soumis = None

    if request.method == "POST":
        statut_soumis = request.POST.get("statut")
        justificatif = request.POST.get("justificatif", "").strip()
        plan_action = request.POST.get("plan_action", "").strip()
        echeance_str = request.POST.get("echeance", "").strip()
        passage_cab = request.POST.get("passage_cab")
        fichier = request.FILES.get("preuve_fichier")
        echeance_val = None

        if statut_soumis not in dict(Traitement.STATUT_CHOICES):
            erreurs["statut"] = "Choisissez un statut valide."
        elif statut_soumis == "en_cours":
            if not plan_action:
                erreurs["plan_action"] = "Le plan d'action est obligatoire pour démarrer le traitement."
            if not echeance_str:
                erreurs["echeance"] = "La date prévisionnelle est obligatoire."
            else:
                try:
                    echeance_val = datetime.strptime(echeance_str, "%Y-%m-%d").date()
                except ValueError:
                    erreurs["echeance"] = "Date invalide."
            if passage_cab not in ("oui", "non"):
                erreurs["passage_cab"] = "Précisez si un passage en CAB est nécessaire."
        elif statut_soumis in ("clos", "non_applicable"):
            if not justificatif:
                erreurs["justificatif"] = "Un justificatif est obligatoire pour clore ou marquer non applicable."

        if not erreurs:
            createur = t is None
            if t is None:
                t = Traitement(id_renseignement_bdp=id_renseignement_bdp, actif=_actif_pour_renseignement(id_renseignement_bdp))
            ancien_statut = t.statut if not createur else None

            t.statut = statut_soumis
            if justificatif:
                t.justificatif = justificatif
            if statut_soumis == "en_cours":
                t.plan_action = plan_action
                t.echeance = echeance_val
                t.passage_cab = passage_cab == "oui"
            if fichier:
                t.preuve_fichier = fichier
            t.save()

            if createur:
                HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
                if statut_soumis != "a_traiter":
                    HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())
            elif ancien_statut != statut_soumis:
                HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())

            return redirect(request.POST.get("next") or "panel:renseignements")

    return render(
        request,
        "panel/traiter.html",
        {
            "renseignement": renseignement,
            "t": t,
            "erreurs": erreurs,
            "statut_soumis": statut_soumis,
            "form_data": request.POST if request.method == "POST" else None,
            "next": request.GET.get("next", ""),
        },
    )


@login_required
def traitement(request):
    """02 · Traitement — file de tous les traitements, filtrable/triable,
    pensee pour supporter un grand volume (chaque ligne renvoie vers la page
    dediee /traiter/ pour l'action)."""
    qs = Traitement.objects.select_related("actif").prefetch_related("historique")
    compteurs = {code: qs.filter(statut=code).count() for code, _ in Traitement.STATUT_CHOICES}
    traitements_total = qs.count()
    aujourdhui = timezone.localdate()
    en_retard_total = qs.filter(echeance__lt=aujourdhui, statut__in=_OUVERTS).count()

    statut = request.GET.get("statut")
    if statut == "en_retard":
        qs = qs.filter(echeance__lt=aujourdhui, statut__in=_OUVERTS)
    elif statut:
        qs = qs.filter(statut=statut)

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    for valeur, borne in ((date_debut, "gte"), (date_fin, "lte")):
        if valeur:
            try:
                d = datetime.strptime(valeur, "%Y-%m-%d").date()
                qs = qs.filter(**{f"maj_le__date__{borne}": d})
            except ValueError:
                pass

    renseignements_par_id = {r.id_renseignement_bdp: r for r in Renseignement.objects.all()}

    q = request.GET.get("q", "").strip()
    traitements = list(qs)
    if q:
        ql = q.lower()
        traitements = [
            t for t in traitements
            if ql in str(t.actif or "").lower()
            or ql in getattr(renseignements_par_id.get(t.id_renseignement_bdp), "titre", "").lower()
            or ql in getattr(renseignements_par_id.get(t.id_renseignement_bdp), "reference_externe", "").lower()
        ]

    criticite_filtre = request.GET.get("criticite")
    if criticite_filtre:
        traitements = [
            t for t in traitements
            if getattr(renseignements_par_id.get(t.id_renseignement_bdp), "criticite", None) == criticite_filtre
        ]

    tri = request.GET.get("tri", "recent")
    if tri == "criticite":
        traitements.sort(key=lambda t: _ORDRE_CRITICITE.get(getattr(renseignements_par_id.get(t.id_renseignement_bdp), "criticite", None), 9))
    elif tri == "echeance":
        traitements.sort(key=lambda t: t.echeance or datetime.max.date())
    else:
        traitements.sort(key=lambda t: t.maj_le, reverse=True)

    traitements_en_retard_apercu = [t for t in traitements if t.en_retard][:5]

    return render(
        request,
        "panel/traitement.html",
        {
            "traitements": traitements,
            "traitements_total": traitements_total,
            "traitements_en_retard_apercu": traitements_en_retard_apercu,
            "en_retard_total": en_retard_total,
            "q": q,
            "criticite_filtre": criticite_filtre,
            "tri": tri,
            "statut_choices": Traitement.STATUT_CHOICES,
            "renseignements_par_id": renseignements_par_id,
            "compteurs": compteurs,
            "statut_filtre": statut,
            "date_debut": date_debut or "",
            "date_fin": date_fin or "",
            "aujourdhui": timezone.localdate(),
        },
    )


@login_required
def definir_echeance(request, pk):
    t = get_object_or_404(Traitement, pk=pk)
    if request.method == "POST":
        valeur = request.POST.get("echeance")
        try:
            t.echeance = datetime.strptime(valeur, "%Y-%m-%d").date() if valeur else None
        except ValueError:
            pass
        else:
            t.save(update_fields=["echeance"])
    return redirect(request.POST.get("next") or "panel:traitement")


@login_required
def export_traitement_pdf(request, pk):
    """Export PDF d'une fiche de traitement — sert de preuve d'audit."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    t = get_object_or_404(Traitement, pk=pk)
    renseignement = Renseignement.objects.filter(id_renseignement_bdp=t.id_renseignement_bdp).first()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="traitement-{t.pk}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 60

    p.setFont("Helvetica-Bold", 15)
    p.drawString(50, y, "Fiche de traitement")
    y -= 18
    p.setFont("Helvetica", 8)
    p.setFillGray(0.4)
    p.drawString(50, y, f"id_renseignement_bdp : {t.id_renseignement_bdp}")
    y -= 30

    p.setFillGray(0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Actif")
    p.setFont("Helvetica", 10)
    p.drawString(160, y, str(t.actif) if t.actif else "—")
    y -= 18

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Renseignement")
    p.setFont("Helvetica", 10)
    p.drawString(160, y, renseignement.titre if renseignement else "(retiré de la BDP)")
    y -= 18

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Statut")
    p.setFont("Helvetica", 10)
    p.drawString(160, y, t.get_statut_display())
    y -= 18

    if t.echeance:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Échéance")
        p.setFont("Helvetica", 10)
        p.drawString(160, y, t.echeance.strftime("%d/%m/%Y") + (" (dépassée)" if t.en_retard else ""))
        y -= 18

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Dernière mise à jour")
    p.setFont("Helvetica", 10)
    p.drawString(160, y, t.maj_le.strftime("%d/%m/%Y %H:%M"))
    y -= 26

    if t.justificatif:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y, "Justificatif")
        y -= 16
        p.setFont("Helvetica", 9)
        for i in range(0, len(t.justificatif), 95):
            p.drawString(50, y, t.justificatif[i : i + 95])
            y -= 13
        y -= 12

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Historique")
    y -= 16
    p.setFont("Helvetica", 9)
    for h in t.historique.all():
        p.drawString(56, y, f"– {h.evenement} : {h.horodatage.strftime('%d/%m/%Y %H:%M')}")
        y -= 13

    p.showPage()
    p.save()
    return response


@login_required
def actualites(request):
    """Flux complet de la BDP, non filtre sur les actifs declares."""
    type_ = request.GET.get("type")
    q = request.GET.get("q", "").strip()
    items = Renseignement.objects.all()
    if type_ in ("technique", "normatif"):
        items = items.filter(type=type_)
    if q:
        items = [
            r for r in items
            if q.lower() in r.titre.lower()
            or q.lower() in r.description.lower()
            or q.lower() in r.source.lower()
        ]
    return render(request, "panel/actualites.html", {"items": items, "type_filtre": type_, "q": q})


@login_required
def organisation(request):
    """Section encore a definir — les actifs ont demenage vers Gestion des
    actifs. Conservee comme entree de menu (dropdown avatar) en attendant de
    decider ce qui y va."""
    return render(request, "panel/organisation.html")


@login_required
def gestion_actifs(request):
    """Page dediee a la gestion des actifs : liste, filtres, actions
    (ajouter/monter en version/supprimer/exporter) + historique des
    modifications, sur le meme principe que Renseignements."""
    import json

    from .taxonomie import REFERENTIELS_NORMATIFS, TAXONOMIE_TECHNIQUE

    actifs = list(ActifClient.objects.all())

    q = request.GET.get("q", "").strip()
    if q:
        actifs = [a for a in actifs if q.lower() in str(a).lower()]

    type_filtre = request.GET.get("type")
    if type_filtre in ("technique", "normatif"):
        actifs = [a for a in actifs if a.type == type_filtre]

    tri = request.GET.get("tri", "az")
    if tri == "nb":
        actifs.sort(key=lambda a: a.traitements.count(), reverse=True)
    else:
        actifs.sort(key=lambda a: str(a))

    # Couverture : un actif sans renseignement matche n'est pas forcement
    # "sain" — le plus souvent, aucune source ingeree ne couvre encore cet
    # editeur/produit (ou ce referentiel). On le signale plutot que de
    # laisser un silence qui pourrait passer pour "rien a signaler".
    actifs_couverts_pks = {r.actif.pk for r in calculer_matching()}

    return render(
        request,
        "panel/gestion_actifs.html",
        {
            "actifs": actifs,
            "actifs_couverts_pks": actifs_couverts_pks,
            "total": ActifClient.objects.count(),
            "nb_technique": ActifClient.objects.filter(type="technique").count(),
            "nb_normatif": ActifClient.objects.filter(type="normatif").count(),
            "nb_non_couverts": ActifClient.objects.count() - len(actifs_couverts_pks),
            "historique": HistoriqueActif.objects.all()[:12],
            "q": q,
            "type_filtre": type_filtre,
            "tri": tri,
            "taxonomie_json": json.dumps(TAXONOMIE_TECHNIQUE),
            "referentiels": REFERENTIELS_NORMATIFS,
        },
    )


@login_required
def ajouter_actif(request):
    """Ajout declaratif d'un actif ou d'un referentiel (brief section 3).
    Declenche le Matching juste apres la modification de profil (jamais a
    l'ouverture du panel)."""
    if request.method == "POST":
        type_ = request.POST.get("type")
        if type_ in ("technique", "normatif"):
            actif = ActifClient.objects.create(
                type=type_,
                categorie=request.POST.get("categorie", "").strip(),
                editeur=request.POST.get("editeur", "").strip(),
                produit=request.POST.get("produit", "").strip(),
                version=request.POST.get("version", "").strip(),
                referentiel=request.POST.get("referentiel", "").strip(),
            )
            HistoriqueActif.objects.create(actif_repr=str(actif), evenement="ajout")
            for resultat in calculer_matching(actifs=[actif]):
                t, created = Traitement.objects.get_or_create(
                    id_renseignement_bdp=resultat.renseignement.id_renseignement_bdp,
                    defaults={"statut": "a_traiter", "actif": actif},
                )
                if created:
                    HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
    return redirect(request.POST.get("next") or "panel:gestion_actifs")


@login_required
def monter_version_actif(request, pk):
    """Change la version d'un actif technique, journalise dans l'historique."""
    actif = get_object_or_404(ActifClient, pk=pk)
    if request.method == "POST":
        nouvelle_version = request.POST.get("version", "").strip()
        if nouvelle_version and nouvelle_version != actif.version:
            HistoriqueActif.objects.create(
                actif_repr=str(actif),
                evenement="version",
                detail=f"{actif.version or '—'} → {nouvelle_version}",
            )
            actif.version = nouvelle_version
            actif.save(update_fields=["version"])
    return redirect(request.POST.get("next") or "panel:gestion_actifs")


@login_required
def importer_actifs_csv(request):
    """Import CSV des actifs — mapping simple vers la taxonomie interne
    (brief section 3, methode 2). Colonnes attendues : type,categorie,
    editeur,produit,version,referentiel."""
    import csv
    import io

    if request.method == "POST" and request.FILES.get("fichier"):
        f = request.FILES["fichier"]
        contenu = f.read().decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(contenu))
        crees = 0
        for ligne in reader:
            type_ = (ligne.get("type") or "").strip().lower()
            if type_ not in ("technique", "normatif"):
                continue
            actif = ActifClient.objects.create(
                type=type_,
                categorie=(ligne.get("categorie") or "").strip(),
                editeur=(ligne.get("editeur") or "").strip(),
                produit=(ligne.get("produit") or "").strip(),
                version=(ligne.get("version") or "").strip(),
                referentiel=(ligne.get("referentiel") or "").strip(),
            )
            crees += 1
            HistoriqueActif.objects.create(actif_repr=str(actif), evenement="ajout", detail="import CSV")
            for resultat in calculer_matching(actifs=[actif]):
                t, created = Traitement.objects.get_or_create(
                    id_renseignement_bdp=resultat.renseignement.id_renseignement_bdp,
                    defaults={"statut": "a_traiter", "actif": actif},
                )
                if created:
                    HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
        from django.contrib import messages
        messages.success(request, f"{crees} actif(s) importé(s).")
    return redirect("panel:gestion_actifs")


@login_required
def exporter_actifs_csv(request):
    """Export CSV de tous les actifs/referentiels declares — meme format que
    l'import, pour rester symetrique."""
    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="actifs.csv"'
    writer = csv.writer(response)
    writer.writerow(["type", "categorie", "editeur", "produit", "version", "referentiel"])
    for a in ActifClient.objects.all():
        writer.writerow([a.type, a.categorie, a.editeur, a.produit, a.version, a.referentiel])
    return response


@login_required
def retirer_actif(request, pk):
    """Retrait d'un actif — le client choisit explicitement de conserver ou
    purger l'historique de traitement associe (brief section 4)."""
    actif = get_object_or_404(ActifClient, pk=pk)
    if request.method == "POST":
        mode = request.POST.get("mode")
        repr_actif = str(actif)
        if mode == "purger":
            Traitement.objects.filter(actif=actif).delete()
            HistoriqueActif.objects.create(actif_repr=repr_actif, evenement="suppression_purge")
        else:
            Traitement.objects.filter(actif=actif).update(actif=None)
            HistoriqueActif.objects.create(actif_repr=repr_actif, evenement="suppression_conserve")
        actif.delete()
    return redirect(request.POST.get("next") or "panel:gestion_actifs")


@login_required
def profil(request):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    if request.method == "POST":
        seuil = request.POST.get("seuil_criticite")
        frequence = request.POST.get("frequence")
        if seuil in dict(PreferenceNotification._meta.get_field("seuil_criticite").choices):
            prefs.seuil_criticite = seuil
        if frequence in dict(PreferenceNotification._meta.get_field("frequence").choices):
            prefs.frequence = frequence
        prefs.save()
        return redirect("panel:profil")
    return render(request, "panel/profil.html", {"prefs": prefs})
