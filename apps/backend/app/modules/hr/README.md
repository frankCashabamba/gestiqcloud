# Módulo: hr (RRHH)

Propósito: empleados, nómina y conceptos.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/hr`.
- Schemas en `interface/http/schemas.py`.

## Componentes clave
- `application` (use cases, dto, ports) para nómina/empleados.
- `infrastructure/repositories.py`: persistencia.

## Notas
- Integra con contabilidad/finanzas para asientos/pagos.
