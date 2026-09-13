from django.contrib import messages
from django.shortcuts import redirect, render

from .models import MessageContact


def landing(request):
    """Page publique (marketing) — appelee directement par
    apps.panel.views.vue_ensemble quand le visiteur n'est pas connecte,
    pour que la page d'accueil reste a la meme URL ('/') que le tableau
    de bord une fois connecte."""
    return render(request, "vitrine/landing.html")


def contact(request):
    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        entreprise = request.POST.get("entreprise", "").strip()
        message_texte = request.POST.get("message", "").strip()
        if nom and email and message_texte:
            MessageContact.objects.create(
                nom=nom, email=email, entreprise=entreprise, message=message_texte
            )
            messages.success(request, "Message envoyé — nous revenons vers vous rapidement.")
        else:
            messages.error(request, "Merci de remplir au moins le nom, l'email et le message.")
    return redirect("/#contact")
