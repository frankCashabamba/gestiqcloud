# Módulo Expenses

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Listado, formulario, detalle y panel de gastos.
- Pago de gastos e integración con producción cuando aplica.

## Parcial

- Integración contable requiere validación con backend y permisos contables.

## Pendiente

- E2E gasto -> pago -> asiento.
- Validar categorías y adjuntos por sector.

## Endpoints usados

- `/api/v1/tenant/expenses/*`

## Permisos

- `expenses:read`
- `expenses:create`
- `expenses:update`
- `expenses:delete`

## Tests mínimos

- Crear gasto.
- Editar gasto.
- Pagar gasto.
- Bloquear acciones sin permiso.
