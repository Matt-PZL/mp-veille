"""
Generation de la fiche de traitement en PDF.

C'est la piece qu'on tend a un auditeur : elle doit refleter exactement ce
qui est en base au moment de l'export. Extraite des anciennes vues Django
lors du passage au front Next.js — l'API est desormais son seul appelant.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.bdc.models import Traitement
from apps.bdp.models import Renseignement


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
