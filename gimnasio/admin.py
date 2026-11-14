from django.contrib import admin

from .models import Membresia, Pago, Plan, Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "correo", "telefono", "creado")
    search_fields = ("nombre", "rut")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "duracion_dias")


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ("socio", "plan", "fecha_inicio", "fecha_vencimiento")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("membresia", "monto", "fecha_pago")
