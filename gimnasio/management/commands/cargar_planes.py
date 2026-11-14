from django.core.management.base import BaseCommand

from gimnasio.models import Plan

# Planes ficticios (RF-02). Se pueden ejecutar varias veces sin duplicar.
PLANES = [
    ("Mensual", 30000, 30),
    ("Trimestral", 80000, 90),
    ("Anual", 290000, 365),
]


class Command(BaseCommand):
    help = "Carga los planes de ejemplo (Mensual, Trimestral y Anual)."

    def handle(self, *args, **options):
        for nombre, precio, dias in PLANES:
            plan, creado = Plan.objects.update_or_create(
                nombre=nombre,
                defaults={"precio": precio, "duracion_dias": dias},
            )
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"Plan {plan.nombre}: {estado}")
