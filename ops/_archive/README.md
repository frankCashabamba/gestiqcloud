# Archivo de Migraciones Históricas

Esta carpeta contiene las **39 migraciones incrementales** aplicadas entre Octubre y Noviembre 2025 que fueron consolidadas en la baseline moderna.

## ⚠️ Advertencia

Estas migraciones están **archivadas** y **NO deben aplicarse** en nuevas instalaciones.

Para instalaciones nuevas, usar: **2025-11-01_000_baseline_modern**

## 📜 Historial Consolidado

### Fase 1: Setup Inicial (Oct 26)
- `2025-10-26_000_baseline` - Baseline original (legacy)
- `2025-10-26_101_add_auth_user_is_staff` - Campo is_staff
- `2025-10-26_102_modulos_tables` - Sistema de módulos
- `2025-10-26_103_extend_schema_migrations` - Extender migraciones
- `2025-10-26_104_add_tenants_legacy_id` - Legacy ID

### Fase 2: UUIDs (Oct 26-27)
- `2025-10-26_200_uuid_complete_migration` - Migración a UUIDs
- `2025-10-27_200_fix_payments_invoice_fk` - Fix FKs payments

### Fase 3: Imports & Products (Oct 27)
- `2025-10-27_205_imports_full_schema` - Schema importación
- `2025-10-27_206_import_items_add_tenant_id` - Tenant ID imports
- `2025-10-27_207_import_items_idem_constraint` - Constraint idempotencia
- `2025-10-27_208_products_modernize_schema` - Modernizar productos
- `2025-10-27_209_auth_user_decouple_tenant` - Desacoplar auth

### Fase 4: Módulos & IA (Oct 27)
- `2025-10-27_300_modulos_core` - Core módulos
- `2025-10-27_400_ia_incidents_alerts` - IA incidentes
- `2025-10-27_500_recipes_professional` - Recetas profesionales

### Fase 5: Sectores & Templates (Oct 28)
- `2025-10-28_128_create_tipo_empresa_negocio` - Tipos empresa
- `2025-10-28_129_create_sector_plantilla_table` - Plantillas sector
- `2025-10-28_130_sector_plantillas_seed` - Seed plantillas
- `2025-10-28_131_add_sector_to_tenants` - Sector en tenants
- `2025-10-28_180_import_column_mappings` - Mapeos importación
- `2025-10-28_200_cleanup_tenant_legacy` - Limpieza tenant

### Fase 6: Clientes & Config (Oct 29)
- `2025-10-29_210_clients_ident_fields` - Campos identificación
- `2025-10-29_211_clients_professional_fields` - Campos profesionales
- `2025-10-29_212_tenant_field_config` - Config campos tenant
- `2025-10-29_213_sector_field_defaults` - Defaults sector
- `2025-10-29_214_field_config_modes` - Modos configuración
- `2025-10-29_215_core_country_catalog` - Catálogo países
- `2025-10-29_216_ref_timezones_locales` - Timezones y locales
- `2025-10-29_217_core_moneda_catalog` - Catálogo monedas

### Fase 7: Warehouses & Inventory (Oct 30 - Nov 1)
- `2025-01-20_125_warehouses` - Almacenes
- `2025-10-30_218_warehouses_add_metadata` - Metadata almacenes
- `2025-11-01_230_pos_uuid_types_cleanup` - Cleanup POS UUIDs
- `2025-11-01_231_stock_alerts_modernize_schema` - Modernizar alertas

### Fase 8: Modernización Inglés (Nov 1)
- `2025-11-01_240_products_english_names` - Productos a inglés
- `2025-11-01_241_tenants_english_names` - Tenants a inglés
- `2025-11-01_242_stock_items_qty` - qty_on_hand → qty

### Fase 9: Fresh Start (Nov 1)
- `2025-11-01_250_fresh_start_english` - Fresh start completo
  - Backup auth_user y modulos
  - Drop todas las tablas
  - Recrear schema 100% inglés

## 🎯 Resultado Final

Todas estas migraciones culminaron en:
**2025-11-01_000_baseline_modern** - Schema consolidado v2.0

## 📊 Estadísticas

- **Total migraciones**: 39
- **Período**: Oct 26 - Nov 1, 2025
- **Cambios principales**:
  - Migración a UUIDs
  - Español → Inglés
  - Legacy → Moderno
  - Sistema de módulos
  - Multi-tenant RLS
  - Fresh start final

## 🔍 Referencia Histórica

Estos archivos se mantienen para:
- Auditoría de cambios
- Comprensión de evolución del schema
- Referencia de decisiones arquitectónicas
- Debugging de issues legacy

## ⚠️ NO Usar en Producción

**Para nuevas instalaciones**:
```bash
# ✅ CORRECTO
docker exec -i db psql -U postgres -d gestiqclouddb_dev < \
  ops/migrations/2025-11-01_000_baseline_modern/up.sql

# ❌ INCORRECTO
# No aplicar migraciones de _archive/
```

---

**Estado**: Archivado
**Reemplazado por**: 2025-11-01_000_baseline_modern
**Fecha de archivo**: Nov 1, 2025
