"""Accounting models."""

# Los módulos contractuales se controlan por tenant en estas tablas:
# - `modulos_modulo`: catálogo de módulos disponibles.
# - `modulos_empresamodulo`: módulos que un tenant ha contratado.
# - `modulos_moduloasignado`: qué usuarios de ese tenant pueden usar cada módulo.
from app.models.accounting.plan_cuentas import PlanCuentas, AsientoContable, AsientoLinea  # noqa: E402

__all__ = ["PlanCuentas", "AsientoContable", "AsientoLinea"]
