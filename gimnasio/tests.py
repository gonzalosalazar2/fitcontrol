from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .acceso import evaluar_acceso
from .forms import MENSAJE_RUT
from .membresias import (
    calcular_vencimiento,
    fecha_inicio_minima,
    formatear_pesos,
    membresia_vigente,
)
from .models import Ingreso, Membresia, Pago, Plan, Socio
from .rut import normalizar_rut, rut_es_valido


class RutTests(SimpleTestCase):
    def test_rut_valido_con_distintos_formatos(self):
        for rut in ["12.345.678-5", "12345678-5", "123456785", "10.000.013-k"]:
            self.assertTrue(rut_es_valido(rut), rut)

    def test_rut_invalido(self):
        for rut in ["12.345.678-9", "", "abc", "12.345.678", "1-9"]:
            self.assertFalse(rut_es_valido(rut), rut)

    def test_normalizar(self):
        self.assertEqual(normalizar_rut("12.345.678-5"), "12345678-5")


class RegistrarSocioTests(TestCase):
    """Casos de prueba de RF-01 (CP-01, CP-02, CP-03) y entradas vacías."""

    def setUp(self):
        self.url = reverse("registrar_socio")
        self.datos = {
            "nombre": "Juan Pérez",
            "rut": "12.345.678-5",
            "correo": "juan.perez@ejemplo.cl",
            "telefono": "912345678",
        }

    def test_cp01_registro_valido(self):
        respuesta = self.client.post(self.url, self.datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Socio.objects.count(), 1)
        self.assertEqual(Socio.objects.get().rut, "12345678-5")

    def test_cp02_rut_duplicado(self):
        self.client.post(self.url, self.datos)
        otro = dict(self.datos, nombre="Pedro Soto", correo="pedro.soto@ejemplo.cl")
        respuesta = self.client.post(self.url, otro)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Socio.objects.count(), 1)
        self.assertIn(MENSAJE_RUT, respuesta.context["form"].errors["rut"])

    def test_cp03_digito_verificador_incorrecto(self):
        datos = dict(self.datos, nombre="Ana Rojas", rut="12.345.678-9")
        respuesta = self.client.post(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Socio.objects.count(), 0)
        self.assertIn(MENSAJE_RUT, respuesta.context["form"].errors["rut"])

    def test_campos_vacios_no_guardan(self):
        respuesta = self.client.post(self.url, {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Socio.objects.count(), 0)
        for campo in ["nombre", "rut", "correo", "telefono"]:
            self.assertIn(campo, respuesta.context["form"].errors)

    def test_correo_invalido_no_guarda(self):
        datos = dict(self.datos, correo="correo-sin-arroba")
        respuesta = self.client.post(self.url, datos)
        self.assertEqual(Socio.objects.count(), 0)
        self.assertIn("correo", respuesta.context["form"].errors)


class ReglasMembresiaTests(SimpleTestCase):
    """Reglas de fechas (lógica pura)."""

    def test_vencimiento_es_inicio_mas_duracion(self):
        self.assertEqual(calcular_vencimiento(date(2026, 11, 14), 30), date(2026, 12, 14))

    def test_vigencia_incluye_el_dia_de_vencimiento(self):
        hoy = date(2026, 11, 14)
        self.assertTrue(membresia_vigente(date(2026, 10, 15), hoy, hoy))  # vence hoy
        self.assertFalse(membresia_vigente(date(2026, 10, 14), hoy - timedelta(days=1), hoy))  # venció ayer
        self.assertFalse(membresia_vigente(hoy + timedelta(days=1), hoy + timedelta(days=31), hoy))  # inicia mañana

    def test_inicio_minimo(self):
        hoy = date(2026, 11, 14)
        self.assertEqual(fecha_inicio_minima(hoy, None), hoy)
        self.assertEqual(fecha_inicio_minima(hoy, date(2026, 11, 20)), date(2026, 11, 21))
        self.assertEqual(fecha_inicio_minima(hoy, hoy), date(2026, 11, 15))
        self.assertEqual(fecha_inicio_minima(hoy, date(2026, 11, 13)), hoy)

    def test_formatear_pesos(self):
        self.assertEqual(formatear_pesos(30000), "$30.000")


class PlanTests(TestCase):
    """RF-02: planes con precio y duración válidos."""

    def test_comando_carga_tres_planes_sin_duplicar(self):
        call_command("cargar_planes", verbosity=0)
        call_command("cargar_planes", verbosity=0)
        self.assertEqual(Plan.objects.count(), 3)
        mensual = Plan.objects.get(nombre="Mensual")
        self.assertEqual((mensual.precio, mensual.duracion_dias), (30000, 30))

    def test_precio_negativo_rechazado(self):
        with self.assertRaises(ValidationError):
            Plan(nombre="Prueba", precio=-5, duracion_dias=30).full_clean()

    def test_precio_cero_rechazado(self):
        with self.assertRaises(ValidationError):
            Plan(nombre="Prueba", precio=0, duracion_dias=30).full_clean()

    def test_duracion_cero_rechazada(self):
        with self.assertRaises(ValidationError):
            Plan(nombre="Prueba", precio=1000, duracion_dias=0).full_clean()


class AsignarPlanTests(TestCase):
    """RF-03: asignar plan y registrar pago (CP-04 y casos relacionados)."""

    def setUp(self):
        call_command("cargar_planes", verbosity=0)
        self.socio = Socio.objects.create(
            nombre="Juan Pérez", rut="12345678-5",
            correo="juan.perez@ejemplo.cl", telefono="912345678",
        )
        self.plan = Plan.objects.get(nombre="Mensual")
        self.url = reverse("asignar_plan", args=[self.socio.id])
        self.hoy = timezone.localdate()

    def datos(self, **cambios):
        base = {
            "plan": self.plan.id,
            "fecha_inicio": self.hoy.isoformat(),
            "monto": self.plan.precio,
            "fecha_pago": self.hoy.isoformat(),
        }
        base.update(cambios)
        return base

    def test_cp04_asignacion_valida(self):
        respuesta = self.client.post(self.url, self.datos())
        self.assertEqual(respuesta.status_code, 302)
        membresia = Membresia.objects.get()
        self.assertEqual(membresia.fecha_vencimiento, self.hoy + timedelta(days=30))
        self.assertEqual(Pago.objects.get().monto, 30000)

    def test_monto_distinto_al_precio_rechazado(self):
        respuesta = self.client.post(self.url, self.datos(monto=20000))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("monto", respuesta.context["form"].errors)
        self.assertEqual(Membresia.objects.count(), 0)
        self.assertEqual(Pago.objects.count(), 0)

    def test_fecha_inicio_anterior_a_hoy_rechazada(self):
        ayer = (self.hoy - timedelta(days=1)).isoformat()
        respuesta = self.client.post(self.url, self.datos(fecha_inicio=ayer))
        self.assertIn("fecha_inicio", respuesta.context["form"].errors)
        self.assertEqual(Membresia.objects.count(), 0)

    def test_fecha_pago_futura_rechazada(self):
        manana = (self.hoy + timedelta(days=1)).isoformat()
        respuesta = self.client.post(self.url, self.datos(fecha_pago=manana))
        self.assertIn("fecha_pago", respuesta.context["form"].errors)
        self.assertEqual(Membresia.objects.count(), 0)

    def test_renovacion_comienza_despues_del_vencimiento(self):
        self.client.post(self.url, self.datos())
        vencimiento = Membresia.objects.get().fecha_vencimiento
        # Mismo día de inicio: se solapa con la membresía actual, debe rechazarse
        rechazada = self.client.post(self.url, self.datos())
        self.assertIn("fecha_inicio", rechazada.context["form"].errors)
        self.assertEqual(Membresia.objects.count(), 1)
        # Día siguiente al vencimiento: se acepta
        siguiente = (vencimiento + timedelta(days=1)).isoformat()
        aceptada = self.client.post(self.url, self.datos(fecha_inicio=siguiente))
        self.assertEqual(aceptada.status_code, 302)
        self.assertEqual(Membresia.objects.count(), 2)

    def test_lista_muestra_estado_vigente(self):
        self.client.post(self.url, self.datos())
        respuesta = self.client.get(reverse("lista_socios"))
        self.assertContains(respuesta, "Vigente")


class ReglaAccesoTests(SimpleTestCase):
    """RF-04: regla de decisión (lógica pura)."""

    hoy = date(2026, 11, 14)

    def test_sin_membresias(self):
        self.assertEqual(evaluar_acceso([], self.hoy), ("sin_plan", None))

    def test_vigente(self):
        periodos = [(self.hoy - timedelta(days=10), self.hoy + timedelta(days=20))]
        self.assertEqual(evaluar_acceso(periodos, self.hoy)[0], "permitido")

    def test_limite_vence_hoy_permite(self):
        periodos = [(self.hoy - timedelta(days=30), self.hoy)]
        self.assertEqual(evaluar_acceso(periodos, self.hoy), ("permitido", self.hoy))

    def test_limite_vencio_ayer_deniega(self):
        ayer = self.hoy - timedelta(days=1)
        periodos = [(self.hoy - timedelta(days=31), ayer)]
        self.assertEqual(evaluar_acceso(periodos, self.hoy), ("vencida", ayer))

    def test_membresia_futura_deniega(self):
        manana = self.hoy + timedelta(days=1)
        periodos = [(manana, manana + timedelta(days=30))]
        self.assertEqual(evaluar_acceso(periodos, self.hoy), ("por_iniciar", manana))

    def test_con_varias_membresias_basta_una_vigente(self):
        periodos = [
            (self.hoy - timedelta(days=90), self.hoy - timedelta(days=60)),  # vencida
            (self.hoy - timedelta(days=5), self.hoy + timedelta(days=25)),   # vigente
        ]
        self.assertEqual(evaluar_acceso(periodos, self.hoy)[0], "permitido")


class RegistrarIngresoTests(TestCase):
    """RF-04: registrar ingreso con validación de membresía (CP-05, CP-06 y otros)."""

    def setUp(self):
        call_command("cargar_planes", verbosity=0)
        self.plan = Plan.objects.get(nombre="Mensual")
        self.url = reverse("registrar_ingreso")
        self.hoy = timezone.localdate()
        self.juan = Socio.objects.create(
            nombre="Juan Pérez", rut="12345678-5",
            correo="juan.perez@ejemplo.cl", telefono="912345678",
        )
        self.maria = Socio.objects.create(
            nombre="María Díaz", rut="11111111-1",
            correo="maria.diaz@ejemplo.cl", telefono="922222222",
        )

    def membresia(self, socio, inicio, vencimiento):
        return Membresia.objects.create(
            socio=socio, plan=self.plan, fecha_inicio=inicio, fecha_vencimiento=vencimiento
        )

    def test_cp05_ingreso_permitido(self):
        self.membresia(self.juan, self.hoy - timedelta(days=10), self.hoy + timedelta(days=20))
        respuesta = self.client.post(self.url, {"rut": "12.345.678-5"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["resultado"]["permitido"])
        self.assertContains(respuesta, "Juan Pérez")
        self.assertEqual(Ingreso.objects.count(), 1)

    def test_cp06_membresia_vencida(self):
        ayer = self.hoy - timedelta(days=1)
        self.membresia(self.maria, self.hoy - timedelta(days=31), ayer)
        respuesta = self.client.post(self.url, {"rut": "11.111.111-1"})
        self.assertFalse(respuesta.context["resultado"]["permitido"])
        self.assertContains(respuesta, "Membresía vencida")
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_limite_membresia_que_vence_hoy_permite(self):
        self.membresia(self.juan, self.hoy - timedelta(days=30), self.hoy)
        respuesta = self.client.post(self.url, {"rut": "12345678-5"})
        self.assertTrue(respuesta.context["resultado"]["permitido"])
        self.assertEqual(Ingreso.objects.count(), 1)

    def test_rut_no_registrado(self):
        respuesta = self.client.post(self.url, {"rut": "10.000.013-K"})
        self.assertFalse(respuesta.context["resultado"]["permitido"])
        self.assertContains(respuesta, "RUT no registrado")
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_rut_con_digito_incorrecto(self):
        respuesta = self.client.post(self.url, {"rut": "12.345.678-9"})
        self.assertFalse(respuesta.context["resultado"]["permitido"])
        self.assertContains(respuesta, "El RUT no es válido")
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_socio_sin_membresia(self):
        respuesta = self.client.post(self.url, {"rut": "12.345.678-5"})
        self.assertFalse(respuesta.context["resultado"]["permitido"])
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_membresia_que_aun_no_comienza(self):
        manana = self.hoy + timedelta(days=1)
        self.membresia(self.juan, manana, manana + timedelta(days=30))
        respuesta = self.client.post(self.url, {"rut": "12.345.678-5"})
        self.assertFalse(respuesta.context["resultado"]["permitido"])
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_ingresos_repetidos_el_mismo_dia_se_registran(self):
        self.membresia(self.juan, self.hoy, self.hoy + timedelta(days=30))
        self.client.post(self.url, {"rut": "12.345.678-5"})
        self.client.post(self.url, {"rut": "12.345.678-5"})
        self.assertEqual(Ingreso.objects.count(), 2)

    def test_rut_vacio_no_registra(self):
        respuesta = self.client.post(self.url, {"rut": ""})
        self.assertIn("rut", respuesta.context["form"].errors)
        self.assertIsNone(respuesta.context["resultado"])
        self.assertEqual(Ingreso.objects.count(), 0)
