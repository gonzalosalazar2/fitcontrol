from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("socios/", views.lista_socios, name="lista_socios"),
    path("socios/nuevo/", views.registrar_socio, name="registrar_socio"),
    path("socios/<int:socio_id>/plan/", views.asignar_plan, name="asignar_plan"),
    path("ingreso/", views.registrar_ingreso, name="registrar_ingreso"),
]
