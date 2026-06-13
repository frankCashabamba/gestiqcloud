# Módulo Historical

Estado: Beta
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Importaciones históricas y vistas de ventas, compras y stock.
- Upload CSV/XLSX.

## Parcial

- Cargas grandes y progreso dependen de backend.
- No debe venderse como importador masivo avanzado sin validación.

## Pendiente

- Background processing completo para cargas pesadas.
- E2E upload -> progreso -> consulta.

## Endpoints usados

- `/api/v1/tenant/historical/*`

## Permisos

- `historical:read`
- `historical:import`
- `historical:delete`

## Tests mínimos

- Subir archivo.
- Ver importaciones.
- Consultar ventas/compras/stock.
- Rechazar archivo duplicado.
