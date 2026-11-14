import re

from django import forms
from django.utils import timezone

from .membresias import fecha_inicio_minima, formatear_pesos
from .models import Plan, Socio
from .rut import normalizar_rut, rut_es_valido

MENSAJE_RUT = "El RUT no es válido o ya está registrado"
MENSAJE_OBLIGATORIO = "Este campo es obligatorio"


class SocioForm(forms.ModelForm):
    """Formulario de RF-01: registrar socio con validación de entradas."""

    class Meta:
        model = Socio
        fields = ["nombre", "rut", "correo", "telefono"]
        labels = {
            "nombre": "Nombre completo",
            "rut": "RUT",
            "correo": "Correo",
            "telefono": "Teléfono",
        }
        error_messages = {
            campo: {"required": MENSAJE_OBLIGATORIO}
            for campo in ["nombre", "rut", "correo", "telefono"]
        }

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres")
        return nombre

    def clean_rut(self):
        rut = normalizar_rut(self.cleaned_data["rut"])
        if rut is None or not rut_es_valido(rut):
            raise forms.ValidationError(MENSAJE_RUT)
        if Socio.objects.filter(rut=rut).exists():
            raise forms.ValidationError(MENSAJE_RUT)
        return rut

    def clean_correo(self):
        return self.cleaned_data["correo"].lower()

    def clean_telefono(self):
        telefono = re.sub(r"[\s-]", "", self.cleaned_data["telefono"])
        if not re.fullmatch(r"\+?\d{8,12}", telefono):
            raise forms.ValidationError("El teléfono debe tener entre 8 y 12 dígitos")
        return telefono


def _widget_fecha():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class AsignarPlanForm(forms.Form):
    """Formulario de RF-03: asignar un plan a un socio y registrar el pago."""

    plan = forms.ModelChoiceField(
        queryset=Plan.objects.all(),
        error_messages={
            "required": MENSAJE_OBLIGATORIO,
            "invalid_choice": "Seleccione un plan válido",
        },
    )
    fecha_inicio = forms.DateField(
        widget=_widget_fecha(),
        error_messages={"required": MENSAJE_OBLIGATORIO, "invalid": "Ingrese una fecha válida"},
    )
    monto = forms.IntegerField(
        min_value=1,
        error_messages={
            "required": MENSAJE_OBLIGATORIO,
            "invalid": "Ingrese un monto válido (solo números)",
            "min_value": "El monto debe ser mayor a cero",
        },
    )
    fecha_pago = forms.DateField(
        widget=_widget_fecha(),
        error_messages={"required": MENSAJE_OBLIGATORIO, "invalid": "Ingrese una fecha válida"},
    )

    def __init__(self, *args, socio, **kwargs):
        super().__init__(*args, **kwargs)
        self.socio = socio
        self.hoy = timezone.localdate()
        self.ultima = socio.ultima_membresia()
        ultimo_vencimiento = self.ultima.fecha_vencimiento if self.ultima else None
        self.inicio_minimo = fecha_inicio_minima(self.hoy, ultimo_vencimiento)
        self.initial.setdefault("fecha_inicio", self.inicio_minimo)
        self.initial.setdefault("fecha_pago", self.hoy)

    def clean_fecha_inicio(self):
        fecha = self.cleaned_data["fecha_inicio"]
        if fecha < self.inicio_minimo:
            if self.ultima and self.ultima.fecha_vencimiento >= self.hoy:
                raise forms.ValidationError(
                    "El socio tiene una membresía hasta el "
                    f"{self.ultima.fecha_vencimiento:%d/%m/%Y}. "
                    f"El nuevo período debe comenzar el {self.inicio_minimo:%d/%m/%Y} o después"
                )
            raise forms.ValidationError("La fecha de inicio no puede ser anterior a hoy")
        return fecha

    def clean_fecha_pago(self):
        fecha = self.cleaned_data["fecha_pago"]
        if fecha > self.hoy:
            raise forms.ValidationError("La fecha de pago no puede ser futura")
        return fecha

    def clean(self):
        datos = super().clean()
        plan = datos.get("plan")
        monto = datos.get("monto")
        if plan is not None and monto is not None and monto != plan.precio:
            self.add_error(
                "monto",
                f"El monto debe ser igual al precio del plan ({formatear_pesos(plan.precio)})",
            )
        return datos
