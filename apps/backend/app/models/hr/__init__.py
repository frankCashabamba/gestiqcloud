"""HR (Human Resources) module models"""
import os

from .empleado import Empleado, Vacacion

# Feature flag: Cargar nominas solo si tablas existen
if os.getenv("ENABLE_NOMINAS_MODULE", "false").lower() == "true":
    from .nomina import Nomina, NominaConcepto, NominaPlantilla
    __all__ = ["Empleado", "Vacacion", "Nomina", "NominaConcepto", "NominaPlantilla"]
else:
    __all__ = ["Empleado", "Vacacion"]
