from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import SocioForm


def inicio(request):
    return render(request, "gimnasio/inicio.html")


def registrar_socio(request):
    if request.method == "POST":
        form = SocioForm(request.POST)
        if form.is_valid():
            socio = form.save()
            messages.success(request, f"Socio {socio.nombre} registrado correctamente")
            return redirect("registrar_socio")
    else:
        form = SocioForm()
    return render(request, "gimnasio/registrar_socio.html", {"form": form})
