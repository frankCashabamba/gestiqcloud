# Módulo: accounting (contabilidad)

Propósito: plan de cuentas, asientos y reportes contables.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/accounting`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica contable.
- `infrastructure/repositories.py`: persistencia de cuentas/asientos.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Depende de finanzas/ventas/compras para generar asientos; revisar integraciones antes de cambios.
- Considerar RLS por `tenant_id` cuando se active.
