from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("socios/nuevo/", views.registrar_socio, name="registrar_socio"),
]
