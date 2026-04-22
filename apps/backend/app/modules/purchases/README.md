# Module: purchases

Purpose: purchase orders and purchase lines.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/purchases`.

## Key Components
- `application/use_cases.py`, `ports.py`, `dto.py`: business logic and contracts.
- `infrastructure/repositories.py`: persistence.
- `interface/http/schemas.py`: request/response schemas.

## Notes
- Integrates with inventory for receipts/stock and accounting for journal entries.
