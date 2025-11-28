# Módulo: pos

Propósito: punto de venta (tickets, turnos, pagos en caja).

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/pos`.
- Conversions: `interface/http/conversions.py` prefix `/pos/receipts`.

## Componentes clave
- `application/use_cases.py`: lógica POS (turnos, recibos, pagos).
- `application/dto.py` y `ports.py` (si existen) para interfaces.
- `infrastructure/repositories.py`: acceso a datos POS.
- `templates/`: plantillas de ticket (58mm/80mm) en `app/templates/pos/`.

## Notas
- Se conecta con `sales` para líneas y con `inventory` para stock.
- Maneja numeración de tickets (ver servicios de numbering).
