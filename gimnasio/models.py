from django.db import models


class Socio(models.Model):
    """Socio del gimnasio (RF-01). Todos los datos son ficticios."""

    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=15, unique=True)  # se guarda como 12345678-5
    correo = models.EmailField()
    telefono = models.CharField(max_length=15)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.rut})"
