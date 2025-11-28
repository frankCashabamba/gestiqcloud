# Módulo: production

Propósito: órdenes de producción y recetas.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/production`.

## Componentes clave
- `application/use_cases.py`, `ports.py`, `dto.py`: lógica de órdenes/recetas.
- `infrastructure/repositories.py`: persistencia.
- `domain/entities.py`: entidades de producción.
- `interface/http/schemas.py`: schemas de request/response.

## Notas
- Integra con inventario para consumo de insumos y con productos para recetas.
