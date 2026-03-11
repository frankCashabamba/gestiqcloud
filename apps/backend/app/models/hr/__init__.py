"""HR Models - Sistema de Recursos Humanos

Incluye:
- Empleados
- Configuración salarial
- Nóminas
- Deducciones
- Boletos
"""

from .employee import Employee, EmployeeDeduction, EmployeeSalary
from .attendance import TimeEntry, VacationRequest
from .payroll import Payroll, PayrollDetail, PayrollTax
from .payslip import PaymentSlip

__all__ = [
    "Employee",
    "EmployeeSalary",
    "EmployeeDeduction",
    "VacationRequest",
    "TimeEntry",
    "Payroll",
    "PayrollDetail",
    "PayrollTax",
    "PaymentSlip",
]
