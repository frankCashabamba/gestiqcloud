"""HR (Human Resources) module models"""

import os

from .employee import Employee, Vacation

# Backward compatibility aliases
Empleado = Employee
Vacacion = Vacation

# Feature flag: load payroll module only if enabled
if os.getenv("ENABLE_PAYROLL_MODULE", "false").lower() == "true":
    from .payroll import Payroll, PayrollConcept, PayrollTemplate

    # Legacy Spanish aliases
    Payroll = Payroll
    PayrollConcepto = PayrollConcept
    PayrollPlantilla = PayrollTemplate

    __all__ = [
        "Empleado",
        "Vacacion",
        "Employee",
        "Vacation",
        "Payroll",
        "PayrollConcept",
        "PayrollTemplate",
        "Payroll",
        "PayrollConcepto",
        "PayrollPlantilla",
    ]
else:
    __all__ = ["Empleado", "Vacacion", "Employee", "Vacation"]
