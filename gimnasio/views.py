from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .acceso import evaluar_acceso
from .forms import AsignarPlanForm, IngresoForm, SocioForm
from .membresias import calcular_vencimiento
from .models import Ingreso, Membresia, Pago, Plan, Socio
from .rut import normalizar_rut, rut_es_valido


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


def lista_socios(request):
    """Lista básica de socios con su estado y acceso a asignar plan."""
    filas = []
    for socio in Socio.objects.all():
        ultima = socio.ultima_membresia()
        filas.append(
            {
                "socio": socio,
                "estado": socio.estado(),
                "vencimiento": ultima.fecha_vencimiento if ultima else None,
                "plan": ultima.plan.nombre if ultima else "",
            }
        )
    return render(request, "gimnasio/lista_socios.html", {"filas": filas})


def asignar_plan(request, socio_id):
    socio = get_object_or_404(Socio, pk=socio_id)
    if request.method == "POST":
        form = AsignarPlanForm(request.POST, socio=socio)
        if form.is_valid():
            plan = form.cleaned_data["plan"]
            inicio_membresia = form.cleaned_data["fecha_inicio"]
            vencimiento = calcular_vencimiento(inicio_membresia, plan.duracion_dias)
            with transaction.atomic():
                membresia = Membresia.objects.create(
                    socio=socio,
                    plan=plan,
                    fecha_inicio=inicio_membresia,
                    fecha_vencimiento=vencimiento,
                )
                Pago.objects.create(
                    membresia=membresia,
                    monto=form.cleaned_data["monto"],
                    fecha_pago=form.cleaned_data["fecha_pago"],
                )
            messages.success(
                request,
                f"Pago registrado. {socio.nombre}: plan {plan.nombre}, "
                f"vence el {vencimiento:%d/%m/%Y}",
            )
            return redirect("lista_socios")
    else:
        form = AsignarPlanForm(socio=socio)
    contexto = {"socio": socio, "form": form, "planes": Plan.objects.all()}
    return render(request, "gimnasio/asignar_plan.html", contexto)


def _denegado(*lineas):
    return {"permitido": False, "lineas": list(lineas)}


def _procesar_ingreso(rut_ingresado):
    """Aplica las reglas de RF-04 y devuelve el resultado a mostrar."""
    rut = normalizar_rut(rut_ingresado)
    if rut is None or not rut_es_valido(rut):
        return _denegado("El RUT no es válido")
    try:
        socio = Socio.objects.get(rut=rut)
    except Socio.DoesNotExist:
        return _denegado("RUT no registrado")

    hoy = timezone.localdate()
    periodos = list(socio.membresias.values_list("fecha_inicio", "fecha_vencimiento"))
    motivo, fecha = evaluar_acceso(periodos, hoy)

    if motivo == "permitido":
        Ingreso.objects.create(socio=socio)
        vigente = socio.membresia_vigente(hoy)
        return {
            "permitido": True,
            "lineas": [
                "Ingreso registrado.",
                f"Socio: {socio.nombre}. Plan: {vigente.plan.nombre}.",
                f"Vence: {fecha:%d/%m/%Y}",
            ],
        }
    if motivo == "vencida":
        return _denegado(f"Membresía vencida el {fecha:%d/%m/%Y}.", "Debe renovar su plan")
    if motivo == "por_iniciar":
        return _denegado(f"La membresía comienza el {fecha:%d/%m/%Y}.")
    return _denegado("El socio no tiene una membresía.", "Debe contratar un plan")


def registrar_ingreso(request):
    resultado = None
    if request.method == "POST":
        form = IngresoForm(request.POST)
        if form.is_valid():
            resultado = _procesar_ingreso(form.cleaned_data["rut"])
    else:
        form = IngresoForm()
    return render(request, "gimnasio/registrar_ingreso.html", {"form": form, "resultado": resultado})
