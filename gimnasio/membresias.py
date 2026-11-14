"""Reglas de membresía (sin dependencias de Django).

Reglas implementadas (propuestas en OBS-02 y OBS-03):
- vencimiento = fecha de inicio + duración del plan en días
- la membresía está vigente si inicio <= hoy <= vencimiento
  (el día de vencimiento todavía es válido)
- si el socio ya tiene una membresía que no ha vencido, el nuevo período
  debe comenzar el día siguiente a su vencimiento; si no, desde hoy
"""
from datetime import timedelta


def calcular_vencimiento(fecha_inicio, duracion_dias):
    return fecha_inicio + timedelta(days=duracion_dias)


def membresia_vigente(fecha_inicio, fecha_vencimiento, hoy):
    return fecha_inicio <= hoy <= fecha_vencimiento


def fecha_inicio_minima(hoy, ultimo_vencimiento=None):
    """Primera fecha de inicio permitida para una nueva membresía."""
    if ultimo_vencimiento is not None and ultimo_vencimiento >= hoy:
        return ultimo_vencimiento + timedelta(days=1)
    return hoy


def formatear_pesos(monto):
    """30000 -> '$30.000'"""
    return "$" + f"{monto:,}".replace(",", ".")
