# Modulo Importador

Este `README.md` es un indice actual. Si hay conflicto con otros documentos, la fuente de verdad es:

1. `ARCHITECTURE.md`
2. `CONVENTIONS.md`
3. `MEJORAS_IMPLEMENTADAS.md`

## Estado actual
- Entrada principal: `ImportadorExcelWithQueue` en `/imports`.
- API frontend: centralizada en `@endpoints/imports`.
- Progreso: polling HTTP a `GET /api/v1/tenant/imports/batches/{id}/status`.
- UI legacy removida del flujo principal.

## Archivos canónicos
- `ARCHITECTURE.md`: arquitectura, rutas y flujos.
- `CONVENTIONS.md`: reglas para endpoints, hooks y servicios.
- `MEJORAS_IMPLEMENTADAS.md`: mejoras ya aplicadas y estado técnico.

## Regla de mantenimiento
- No agregar planes/sprints históricos dentro de este módulo.
- No documentar endpoints hardcodeados en texto libre; usar `@endpoints/imports`.
