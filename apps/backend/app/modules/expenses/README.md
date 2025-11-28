# Módulo: expenses

Propósito: gestión de gastos.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/expenses`.

## Componentes clave
- `application/use_cases.py`, `dto.py`, `ports.py` (si existen).
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Puede cruzar con finanzas/contabilidad para reflejar en caja/bancos/asientos.
