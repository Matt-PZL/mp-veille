from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.bdc.models import ActifClient, HistoriqueTraitement, PreferenceNotification, Traitement
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

_ORDRE_STATUT = {"a_traiter": 0, "en_cours": 1, "clos": 2, "non_applicable": 3}


def _actif_pour_renseignement(id_renseignement_bdp, resultats=None):
    """Retrouve l'actif client associe a un renseignement via le Matching
    (lecture seule) — sert a rattacher un Traitement au bon actif."""
    resultats = resultats if resultats is not None else calculer_matching()
    for resultat in resultats:
        if resultat.renseignement.id_renseignement_bdp == id_renseignement_bdp:
            return resultat.actif
    return None


@login_required
def renseignements(request):
    """01 · Renseignements sur les actifs — axe actifs a gauche, liste a droite."""
    actifs = list(ActifClient.objects.all())
    tri_actifs = request.GET.get("tri_actifs", "az")
    if tri_actifs == "nb":
        actifs.sort(key=lambda a: a.traitements.count(), reverse=True)
    else:
        actifs.sort(key=lambda a: str(a))

    actif_selectionne = None
    actif_id = request.GET.get("actif")
    if actif_id:
        actif_selectionne = next((a for a in actifs if str(a.pk) == actif_id), None)

    if actif_selectionne:
        items = [
            r.renseignement
            for r in calculer_matching(actifs=[actif_selectionne])
        ]
    else:
        items = list(Renseignement.objects.all())

    traitements_par_id = {t.id_renseignement_bdp: t for t in Traitement.objects.all()}

    tri = request.GET.get("tri", "date")
    if tri == "statut":
        items.sort(key=lambda r: _ORDRE_STATUT.get(
            getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter"), 0
        ))
    else:
        items.sort(key=lambda r: r.decouvert_le, reverse=True)

    return render(
        request,
        "panel/renseignements.html",
        {
            "actifs": actifs,
            "items": items,
            "traitements_par_id": traitements_par_id,
            "actif_selectionne": actif_selectionne,
            "tri": tri,
            "tri_actifs": tri_actifs,
        },
    )


@login_required
def demarrer_traitement(request, id_renseignement_bdp):
    """Cree explicitement un Traitement 'a_traiter' pour un renseignement qui
    n'en a pas encore — un statut resulte toujours d'une action volontaire
    (brief section 4), jamais d'une valeur preremplie."""
    if request.method == "POST":
        renseignement = get_object_or_404(Renseignement, id_renseignement_bdp=id_renseignement_bdp)
        actif = _actif_pour_renseignement(renseignement.id_renseignement_bdp)
        t, created = Traitement.objects.get_or_create(
            id_renseignement_bdp=renseignement.id_renseignement_bdp,
            defaults={"statut": "a_traiter", "actif": actif},
        )
        if created:
            HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
    return redirect(request.POST.get("next") or "panel:renseignements")


@login_required
def traitement(request):
    """02 · Traitement — axe statuts a gauche, liste Actif|Renseignement a droite."""
    qs = Traitement.objects.select_related("actif").prefetch_related("historique")
    compteurs = {code: qs.filter(statut=code).count() for code, _ in Traitement.STATUT_CHOICES}

    statut = request.GET.get("statut")
    if statut:
        qs = qs.filter(statut=statut)

    renseignements_par_id = {r.id_renseignement_bdp: r for r in Renseignement.objects.all()}

    return render(
        request,
        "panel/traitement.html",
        {
            "traitements": qs,
            "traitements_total": Traitement.objects.count(),
            "renseignements_par_id": renseignements_par_id,
            "compteurs": compteurs,
            "statut_filtre": statut,
        },
    )


@login_required
def marquer_traitement(request, pk):
    """Ecrit directement (id_client implicite via session, statut, horodatage[,
    justificatif]) dans la BDC — jamais via le Matching (brief section 2)."""
    t = get_object_or_404(Traitement, pk=pk)
    if request.method == "POST":
        nouveau_statut = request.POST.get("statut")
        justificatif = request.POST.get("justificatif", "")
        if nouveau_statut in dict(Traitement.STATUT_CHOICES):
            t.statut = nouveau_statut
            if justificatif:
                t.justificatif = justificatif
            t.save()
            HistoriqueTraitement.objects.create(
                traitement=t, evenement=t.get_statut_display()
            )
    return redirect("panel:traitement")


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
    items = Renseignement.objects.all()
    return render(request, "panel/actualites.html", {"items": items})


@login_required
def organisation(request):
    actifs = ActifClient.objects.all()
    return render(request, "panel/organisation.html", {"actifs": actifs})


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
            for resultat in calculer_matching(actifs=[actif]):
                t, created = Traitement.objects.get_or_create(
                    id_renseignement_bdp=resultat.renseignement.id_renseignement_bdp,
                    defaults={"statut": "a_traiter", "actif": actif},
                )
                if created:
                    HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
    return redirect("panel:organisation")


@login_required
def retirer_actif(request, pk):
    """Retrait d'un actif — le client choisit explicitement de conserver ou
    purger l'historique de traitement associe (brief section 4)."""
    actif = get_object_or_404(ActifClient, pk=pk)
    if request.method == "POST":
        mode = request.POST.get("mode")
        if mode == "purger":
            Traitement.objects.filter(actif=actif).delete()
        else:
            Traitement.objects.filter(actif=actif).update(actif=None)
        actif.delete()
    return redirect("panel:organisation")


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
