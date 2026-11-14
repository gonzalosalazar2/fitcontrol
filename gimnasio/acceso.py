"""Regla de acceso al gimnasio (RF-04), sin dependencias de Django.

Reglas implementadas (propuestas en OBS-03):
- el acceso se permite si alguna membresía cumple inicio <= hoy <= vencimiento
  (el día de vencimiento todavía es válido)
- si no hay ninguna vigente, se informa el motivo: sin plan, por iniciar o vencida
"""


def evaluar_acceso(periodos, hoy):
    """Decide si un socio puede ingresar.

    periodos: lista de tuplas (fecha_inicio, fecha_vencimiento), una por membresía.
    Devuelve (motivo, fecha) con motivo en:
      'permitido'   -> fecha = vencimiento más lejano entre las vigentes
      'sin_plan'    -> fecha = None
      'por_iniciar' -> fecha = próxima fecha de inicio
      'vencida'     -> fecha = último vencimiento
    """
    if not periodos:
        return ("sin_plan", None)
    vigentes = [venc for inicio, venc in periodos if inicio <= hoy <= venc]
    if vigentes:
        return ("permitido", max(vigentes))
    futuros = [inicio for inicio, _ in periodos if inicio > hoy]
    if futuros:
        return ("por_iniciar", min(futuros))
    return ("vencida", max(venc for _, venc in periodos))
