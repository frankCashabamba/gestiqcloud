# Migración 2025-10-28_131: Añadir Sector a Tenants

## Propósito
Añade columnas para almacenar el sector y plantilla de sector aplicada a cada tenant.

## Cambios
- Añade `sector_id` (FK a core_tipoempresa)
- Añade `sector_plantilla_nombre` (nombre de la plantilla aplicada)
- Índices para mejor performance

## Dependencias
- 2025-10-28_128: core_tipoempresa debe existir
- 2025-10-28_129: core_sectorplantilla debe existir
