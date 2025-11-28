# Módulo: finanzas

Propósito: caja, bancos y conciliaciones básicas.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/finance`.
- Schemas en `interface/http/schemas.py`.

## Componentes clave
- `application/use_cases.py` y `modules_catalog` si aplica.
- `infrastructure/repositories.py`: persistencia de caja/bancos.
- `types/schemas` según módulo.

## Notas
- Integra con contabilidad para asientos y con payments para conciliación.
