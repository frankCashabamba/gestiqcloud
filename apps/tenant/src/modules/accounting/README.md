# Módulo Accounting

Estado: Beta
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Panel contable, plan de cuentas, asientos, libro diario, libro mayor, P&G y balance.
- Configuración contable POS y métodos de pago.
- Rutas protegidas por `accounting:read`.

## Parcial

- Backend usa permisos granulares con punto (`accounting.entry.*`) mientras frontend conserva permisos resumidos.
- El ciclo contable completo requiere validación con ventas, compras, caja y cierre.

## Pendiente

- Alinear permisos frontend/backend.
- Smoke test apertura -> venta -> compra -> caja -> asiento -> cierre.

## Endpoints usados

- `/api/v1/tenant/accounting/*`
- `/api/v1/tenant/pos/*` para integración POS contable.

## Permisos

- `accounting:read`
- `accounting:entry`
- `accounting:adjust`
- Backend granular: `accounting.entry.create|post|cancel`, `accounting.period.manage`.

## Tests mínimos

- Ver panel contable.
- Crear y postear asiento.
- Cancelar asiento si el permiso existe.
- Validar P&G y balance con datos de prueba.
