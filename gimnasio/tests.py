from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .forms import MENSAJE_RUT
from .models import Socio
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

    url = None

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
