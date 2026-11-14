import re

from django import forms

from .models import Socio
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
