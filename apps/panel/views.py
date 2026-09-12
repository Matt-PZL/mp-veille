from collections import Counter
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bdc.models import (
    ActifClient,
    HistoriqueTraitement,
    PreferenceNotification,
    RenseignementConsulte,
    Traitement,
)
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching

_ORDRE_STATUT = {"a_traiter": 0, "en_cours": 1, "clos": 2, "non_applicable": 3}
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

    ouverts = [
        r for r in tous_renseignements
        if getattr(traitements_par_id.get(r.id_renseignement_bdp), "statut", "a_traiter") in _OUVERTS
    ]
    par_criticite = Counter(r.criticite or "moyenne" for r in ouverts)

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
        .filter(echeance__lt=timezone.localdate(), statut__in=_OUVERTS)
        .order_by("echeance")[:5]
    )
    renseignements_par_id = {r.id_renseignement_bdp: r for r in tous_renseignements}

    return render(
        request,
        "panel/dashboard.html",
        {
            "par_criticite": par_criticite,
            "actifs_exposes": actifs_exposes,
            "taux_cloture": taux_cloture,
            "total_traitements": total_traitements,
            "delai_moyen_jours": delai_moyen_jours,
            "en_retard": en_retard,
            "renseignements_par_id": renseignements_par_id,
            "derniers_renseignements": tous_renseignements[:5],
            "nb_ouverts": len(ouverts),
            "nb_total_renseignements": len(tous_renseignements),
        },
    )


@login_required
def renseignements(request):
    """01 · Renseignements sur les actifs — axe actifs (en arborescence
    technique/normatif) a gauche, liste a droite."""
    actifs = list(ActifClient.objects.all())
    tri_actifs = request.GET.get("tri_actifs", "az")
    if tri_actifs == "nb":
        actifs.sort(key=lambda a: a.traitements.count(), reverse=True)
    else:
        actifs.sort(key=lambda a: str(a))
    actifs_technique = [a for a in actifs if a.type == "technique"]
    actifs_normatif = [a for a in actifs if a.type == "normatif"]

    actif_selectionne = None
    actif_id = request.GET.get("actif")
    if actif_id:
        actif_selectionne = next((a for a in actifs if str(a.pk) == actif_id), None)

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
            "actifs_technique": actifs_technique,
            "actifs_normatif": actifs_normatif,
            "nb_actifs": len(actifs),
            "items": items,
            "traitements_par_id": traitements_par_id,
            "consultes": consultes,
            "actif_selectionne": actif_selectionne,
            "type_selectionne": type_selectionne,
            "tri": tri,
            "tri_actifs": tri_actifs,
        },
    )


@login_required
def marquer_consulte(request, id_renseignement_bdp):
    if request.method == "POST":
        RenseignementConsulte.objects.get_or_create(id_renseignement_bdp=id_renseignement_bdp)
    return JsonResponse({"ok": True})


@login_required
def definir_traitement(request, id_renseignement_bdp):
    """Choix direct du statut (À traiter/En cours/Clos/Non applicable) +
    justificatif, depuis l'écran Renseignements — cree le Traitement s'il
    n'existe pas encore."""
    if request.method == "POST":
        renseignement = get_object_or_404(Renseignement, id_renseignement_bdp=id_renseignement_bdp)
        statut = request.POST.get("statut")
        justificatif = request.POST.get("justificatif", "").strip()
        if statut in dict(Traitement.STATUT_CHOICES):
            actif = _actif_pour_renseignement(renseignement.id_renseignement_bdp)
            t, created = Traitement.objects.get_or_create(
                id_renseignement_bdp=renseignement.id_renseignement_bdp,
                defaults={"statut": statut, "actif": actif, "justificatif": justificatif},
            )
            if created:
                HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
                if statut != "a_traiter":
                    HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())
            else:
                statut_a_change = t.statut != statut
                t.statut = statut
                t.justificatif = justificatif
                t.save()
                if statut_a_change:
                    HistoriqueTraitement.objects.create(traitement=t, evenement=t.get_statut_display())
    return redirect(request.POST.get("next") or "panel:renseignements")


@login_required
def traitement(request):
    """02 · Traitement — axe statuts a gauche, liste Actif|Renseignement a droite."""
    qs = Traitement.objects.select_related("actif").prefetch_related("historique")
    compteurs = {code: qs.filter(statut=code).count() for code, _ in Traitement.STATUT_CHOICES}
    traitements_total = qs.count()

    statut = request.GET.get("statut")
    if statut:
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

    return render(
        request,
        "panel/traitement.html",
        {
            "traitements": qs,
            "traitements_total": traitements_total,
            "renseignements_par_id": renseignements_par_id,
            "compteurs": compteurs,
            "statut_filtre": statut,
            "date_debut": date_debut or "",
            "date_fin": date_fin or "",
            "aujourdhui": timezone.localdate(),
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
    import json

    from .taxonomie import REFERENTIELS_NORMATIFS, TAXONOMIE_TECHNIQUE

    actifs = ActifClient.objects.all()
    return render(
        request,
        "panel/organisation.html",
        {
            "actifs": actifs,
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
            for resultat in calculer_matching(actifs=[actif]):
                t, created = Traitement.objects.get_or_create(
                    id_renseignement_bdp=resultat.renseignement.id_renseignement_bdp,
                    defaults={"statut": "a_traiter", "actif": actif},
                )
                if created:
                    HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
    return redirect("panel:organisation")


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
            for resultat in calculer_matching(actifs=[actif]):
                t, created = Traitement.objects.get_or_create(
                    id_renseignement_bdp=resultat.renseignement.id_renseignement_bdp,
                    defaults={"statut": "a_traiter", "actif": actif},
                )
                if created:
                    HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
        from django.contrib import messages
        messages.success(request, f"{crees} actif(s) importé(s).")
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
