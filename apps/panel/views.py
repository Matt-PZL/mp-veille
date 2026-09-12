from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.bdc.models import ActifClient, HistoriqueTraitement, PreferenceNotification, Traitement
from apps.bdp.models import Renseignement


@login_required
def renseignements(request):
    """01 · Renseignements sur les actifs — axe actifs a gauche, liste a droite."""
    actifs = ActifClient.objects.all()
    items = Renseignement.objects.all()
    traitements_par_id = {
        t.id_renseignement_bdp: t for t in Traitement.objects.all()
    }
    return render(
        request,
        "panel/renseignements.html",
        {"actifs": actifs, "items": items, "traitements_par_id": traitements_par_id},
    )


@login_required
def traitement(request):
    """02 · Traitement — axe statuts a gauche, liste Actif|Renseignement a droite."""
    traitements = Traitement.objects.select_related("actif").prefetch_related("historique")
    renseignements_par_id = {
        r.id_renseignement_bdp: r for r in Renseignement.objects.all()
    }
    compteurs = {
        code: traitements.filter(statut=code).count()
        for code, _ in Traitement.STATUT_CHOICES
    }
    return render(
        request,
        "panel/traitement.html",
        {
            "traitements": traitements,
            "renseignements_par_id": renseignements_par_id,
            "compteurs": compteurs,
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
def actualites(request):
    """Flux complet de la BDP, non filtre sur les actifs declares."""
    items = Renseignement.objects.all()
    return render(request, "panel/actualites.html", {"items": items})


@login_required
def organisation(request):
    actifs = ActifClient.objects.all()
    return render(request, "panel/organisation.html", {"actifs": actifs})


@login_required
def profil(request):
    prefs, _ = PreferenceNotification.objects.get_or_create(user=request.user)
    return render(request, "panel/profil.html", {"prefs": prefs})
