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


def export_actifs_pdf(actifs, *, couverts, filtres, nom_fichier):
    """Export PDF de l'inventaire des actifs, tel que filtre a l'ecran.

    Le bandeau rappelle les filtres appliques : un inventaire partiel qu'on
    prendrait pour l'inventaire complet serait trompeur en revue d'audit.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    from django.utils import timezone

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'

    format_page = landscape(A4)
    largeur, hauteur = format_page
    p = canvas.Canvas(response, pagesize=format_page)

    # (libelle, x, largeur utile avant troncature)
    colonnes = [
        ("Type", 40, 60),
        ("Catégorie", 105, 110),
        ("Éditeur", 220, 110),
        ("Produit / Référentiel", 335, 190),
        ("Version", 530, 80),
        ("Couverture", 615, 90),
        ("Déclaré le", 710, 80),
    ]

    def tronquer(texte, largeur_max, police, taille):
        texte = texte or "—"
        if p.stringWidth(texte, police, taille) <= largeur_max:
            return texte
        while texte and p.stringWidth(texte + "…", police, taille) > largeur_max:
            texte = texte[:-1]
        return texte + "…"

    def entete_tableau(y):
        p.setFillGray(0)
        p.setFont("Helvetica-Bold", 8)
        for libelle, x, largeur_col in colonnes:
            p.drawString(x, y, tronquer(libelle, largeur_col, "Helvetica-Bold", 8))
        y -= 6
        p.setStrokeGray(0.7)
        p.line(40, y, largeur - 40, y)
        return y - 14

    # Bandeau de tete, page 1 uniquement.
    y = hauteur - 45
    p.setFont("Helvetica-Bold", 15)
    p.drawString(40, y, "Inventaire des actifs")
    y -= 16

    actives = []
    if filtres.get("type"):
        actives.append(f"type = {filtres['type']}")
    if filtres.get("q"):
        actives.append(f"recherche « {filtres['q']} »")
    if filtres.get("etat"):
        actives.append(f"état = {filtres['etat']}")

    p.setFont("Helvetica", 8)
    p.setFillGray(0.4)
    p.drawString(40, y, f"Édité le {timezone.localtime():%d/%m/%Y à %H:%M} — {len(actifs)} actif(s)")
    y -= 11
    p.drawString(40, y, "Filtres : " + (", ".join(actives) if actives else "aucun (inventaire complet)"))
    y -= 22

    y = entete_tableau(y)

    p.setFont("Helvetica", 8)
    for a in actifs:
        # Nouvelle page avant de mordre sur la marge basse.
        if y < 45:
            p.showPage()
            y = entete_tableau(hauteur - 45)
            p.setFont("Helvetica", 8)

        valeurs = [
            a.get_type_display(),
            a.categorie,
            a.editeur,
            str(a),
            a.version,
            "Couvert" if a.pk in couverts else "Non couvert",
            a.ajoute_le.strftime("%d/%m/%Y"),
        ]
        for (_, x, largeur_col), valeur in zip(colonnes, valeurs):
            # « Non couvert » ressort en gras : c'est l'angle mort a repérer.
            gras = valeur == "Non couvert"
            p.setFont("Helvetica-Bold" if gras else "Helvetica", 8)
            p.setFillGray(0 if gras else 0.15)
            p.drawString(x, y, tronquer(str(valeur), largeur_col, "Helvetica", 8))
        y -= 15

    if not actifs:
        p.setFont("Helvetica-Oblique", 9)
        p.setFillGray(0.45)
        p.drawString(40, y, "Aucun actif ne correspond aux filtres appliqués.")

    p.showPage()
    p.save()
    return response
