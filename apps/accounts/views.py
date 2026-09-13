from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def inscription(request):
    if request.user.is_authenticated:
        return redirect("panel:dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("panel:dashboard")
    else:
        form = UserCreationForm()

    return render(request, "accounts/inscription.html", {"form": form})
