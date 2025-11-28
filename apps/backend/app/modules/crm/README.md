# Módulo: crm

Propósito: leads, oportunidades y CRM ligero.

## Endpoints
- Tenant: `presentation/tenant.py` prefix `/crm`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica de CRM.
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Relacionado con `clients` y ventas.
- Revisar permisos por rol/tenant.
