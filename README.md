# FitControl

Sistema web de control de socios, pagos y asistencia para un gimnasio ficticio.
Proyecto individual de la asignatura Ingeniería de Software (Evaluación 3), Instituto Profesional Virginio Gómez.

Autor: Gonzalo Alonso Salazar Godoy

> Todos los datos del sistema son ficticios. No contiene credenciales ni datos personales reales.

## Alcance

Funcionalidades prioritarias comprometidas:

- RF-01 Registrar socio
- RF-03 Asignar plan y registrar pago
- RF-04 Registrar ingreso (check-in) con validación de membresía vigente

Requisitos pendientes: se declararán al cierre del proyecto en la matriz de trazabilidad.

## Requisitos de ejecución

- Python 3.10 o superior
- Django (se instala con pip)
- No requiere servidor de base de datos: usa SQLite

## Instalación y ejecución

1. Clonar o descomprimir el proyecto y abrir una terminal en la carpeta.
2. Crear y activar el entorno virtual:
   - Windows: `python -m venv venv` y luego `venv\Scripts\activate`
   - Linux/Mac: `python3 -m venv venv` y luego `source venv/bin/activate`
3. Instalar dependencias: `pip install -r requirements.txt`
4. Crear la base de datos: `python manage.py migrate`
5. (Opcional) Cargar datos ficticios: _pendiente de definir_
6. Iniciar el sistema: `python manage.py runserver`
7. Abrir en el navegador: http://127.0.0.1:8000

## Flujo principal

Registrar socio → asignar plan y registrar pago → registrar ingreso → el sistema valida si la membresía está vigente.

## Pruebas

_Se completará en la Semana 3 con el comando para ejecutar las pruebas y la ubicación de las evidencias._

## Versión evaluada

- Repositorio: _enlace pendiente_
- Commit evaluado: _pendiente_
