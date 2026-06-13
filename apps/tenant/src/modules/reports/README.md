# Módulo Reports

Estado: Parcial
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Reportes de ventas, inventario, financiero, resultado real y márgenes.

## Parcial

- Cálculos dependen de fuentes backend y datos reales.
- Reportes avanzados quedan por validar.

## Pendiente

- Documentar fórmulas.
- Validar contra fixtures contables.

## Endpoints usados

- `/api/v1/tenant/reports/*`
- `/api/v1/tenant/dashboard/*`

## Permisos

- `reports:read`
- `reports:export`

## Tests mínimos

- Abrir cada reporte.
- Validar empty state.
- Exportar cuando aplique.
- Comparar un KPI con fixture.
