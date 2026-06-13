# Módulo Analytics

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Dashboard de KPIs del tenant.
- KPIs por sector cuando el backend los expone.

## Parcial

- Los cálculos dependen de fuentes backend y datos reales.
- Falta validación de negocio por sector.

## Pendiente

- Documentar fórmulas de KPIs.
- Smoke test con fixtures conocidos.

## Endpoints usados

- `/api/v1/tenant/dashboard/kpis`

## Permisos

- `analytics:read`

## Tests mínimos

- Cargar dashboard.
- Validar empty state.
- Validar que un usuario sin permiso no accede.
