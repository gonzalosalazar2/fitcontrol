"""Funciones para validar RUT chileno (sin dependencias de Django).

Regla de validación (OBS-01): el RUT se acepta con o sin puntos y guion,
el cuerpo debe tener 7 u 8 dígitos y el dígito verificador se calcula con
el método módulo 11.
"""


def normalizar_rut(valor):
    """Devuelve el RUT como 'cuerpo-DV' (sin puntos, DV en mayúscula).

    Devuelve None si el formato no es válido.
    """
    if valor is None:
        return None
    limpio = valor.replace(".", "").replace("-", "").replace(" ", "").upper()
    if len(limpio) < 2:
        return None
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit() or not (7 <= len(cuerpo) <= 8):
        return None
    if not (dv.isdigit() or dv == "K"):
        return None
    return f"{cuerpo}-{dv}"


def calcular_dv(cuerpo):
    """Calcula el dígito verificador de un cuerpo numérico (módulo 11)."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def rut_es_valido(valor):
    """True si el RUT tiene formato correcto y dígito verificador correcto."""
    rut = normalizar_rut(valor)
    if rut is None:
        return False
    cuerpo, dv = rut.split("-")
    return calcular_dv(cuerpo) == dv
