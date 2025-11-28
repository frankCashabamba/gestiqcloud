# Módulo: clients (clientes)

Propósito: gestión de clientes (core CRM).

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/clientes`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica de clientes.
- `infrastructure/repositories.py`: persistencia.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Se integra con CRM/opportunities y ventas.
- Campos configurables por tenant/sector vía módulo `settings` (form modes).
