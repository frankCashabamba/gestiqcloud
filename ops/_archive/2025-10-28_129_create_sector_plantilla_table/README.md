# Migración: Crear Tabla core_sectorplantilla

## Objetivo
Crear la tabla `core_sectorplantilla` para almacenar plantillas de configuración por sector de negocio.

## Cambios

### Tabla creada
- `core_sectorplantilla`
  - `id` SERIAL PRIMARY KEY
  - `nombre` VARCHAR(255) UNIQUE
  - `tipo_empresa_id` FK a core_tipoempresa
  - `tipo_negocio_id` FK a core_tiponegocio  
  - `config_json` JSONB (configuración completa)
  - `created_at` TIMESTAMPTZ
  - `updated_at` TIMESTAMPTZ (auto-actualizado con trigger)

### Índices
- `idx_sector_plantilla_tipo_empresa`
- `idx_sector_plantilla_tipo_negocio`

## Orden de Aplicación
1. **Primero**: Esta migración (crea tabla vacía)
2. **Segundo**: `2025-10-28_130_sector_plantillas_seed` (inserta datos)

## Notas
- La tabla usa JSONB para `config_json` (más eficiente que JSON)
- Trigger automático para `updated_at`
- Referencias a `core_tipoempresa` y `core_tiponegocio` son OPCIONALES (SET NULL)
