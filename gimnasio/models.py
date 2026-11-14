from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .membresias import formatear_pesos, membresia_vigente


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

    def ultima_membresia(self):
        """Membresía con la fecha de vencimiento más lejana (o None)."""
        return self.membresias.order_by("-fecha_vencimiento").first()

    def membresia_vigente(self, hoy=None):
        hoy = hoy or timezone.localdate()
        return (
            self.membresias.filter(fecha_inicio__lte=hoy, fecha_vencimiento__gte=hoy)
            .order_by("-fecha_vencimiento")
            .first()
        )

    def estado(self, hoy=None):
        hoy = hoy or timezone.localdate()
        if self.membresia_vigente(hoy):
            return "Vigente"
        ultima = self.ultima_membresia()
        if ultima is None:
            return "Sin plan"
        if ultima.fecha_inicio > hoy:
            return "Por iniciar"
        return "Vencida"


class Plan(models.Model):
    """Plan de membresía (RF-02). Precio y duración deben ser mayores a cero."""

    nombre = models.CharField(max_length=50, unique=True)
    precio = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    duracion_dias = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["duracion_dias"]

    def __str__(self):
        return f"{self.nombre} ({formatear_pesos(self.precio)}, {self.duracion_dias} días)"


class Membresia(models.Model):
    """Período de un plan asignado a un socio (RF-03)."""

    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="membresias")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="membresias")
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField()

    class Meta:
        ordering = ["-fecha_vencimiento"]

    def __str__(self):
        return f"{self.socio.nombre}: {self.plan.nombre} hasta {self.fecha_vencimiento:%d/%m/%Y}"

    def esta_vigente(self, hoy=None):
        hoy = hoy or timezone.localdate()
        return membresia_vigente(self.fecha_inicio, self.fecha_vencimiento, hoy)


class Pago(models.Model):
    """Pago asociado a una membresía (RF-03)."""

    membresia = models.OneToOneField(Membresia, on_delete=models.CASCADE, related_name="pago")
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fecha_pago = models.DateField()

    def __str__(self):
        return f"Pago {formatear_pesos(self.monto)} el {self.fecha_pago:%d/%m/%Y}"
