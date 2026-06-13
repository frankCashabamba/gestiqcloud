# Módulo Reconciliation

Estado: Beta
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Dashboard, importación de extractos y detalle de statement.
- Matching y resolución según backend.

## Parcial

- Providers, refunds y payloads reales requieren validación.

## Pendiente

- Upload bancario real por formato.
- E2E conciliación con fixture conocido.

## Endpoints usados

- `/api/v1/tenant/reconciliation/*`

## Permisos

- `reconciliation:read`
- `reconciliation:match`
- `reconciliation:resolve`

## Tests mínimos

- Importar extracto.
- Ver detalle.
- Conciliar movimiento.
- Resolver diferencia.
