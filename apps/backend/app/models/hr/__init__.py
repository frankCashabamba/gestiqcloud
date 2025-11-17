"""HR (Human Resources) module models"""

import os

from .empleado import Employee, Vacation

# Keep old names for backward compatibility during migration
Empleado = Employee
Vacacion = Vacation

# Feature flag: Cargar nominas solo si tablas existen
if os.getenv("ENABLE_NOMINAS_MODULE", "false").lower() == "true":
    from .nomina import Nomina, NominaConcepto, NominaPlantilla

    __all__ = [
        "Empleado",
        "Vacacion",
        "Employee",
        "Vacation",
        "Nomina",
        "NominaConcepto",
        "NominaPlantilla",
    ]
else:
    __all__ = ["Empleado", "Vacacion", "Employee", "Vacation"]
