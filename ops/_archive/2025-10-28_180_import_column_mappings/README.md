# Migración: Import Column Mappings

**Fecha**: 2025-10-28
**Propósito**: Sistema de mapeo inteligente de columnas para importación

## Descripción

Permite guardar configuraciones de mapeo de columnas Excel a campos del sistema,
facilitando importaciones repetidas de archivos con formatos custom de clientes.

## Tabla: import_column_mappings

Guarda mapeos reutilizables por tenant.

**Ejemplo de uso:**

Cliente envía Excel con columnas:
- "FORMATO DE COMO APUNTAR LAS COMPRAS"
- "Precio $"
- "Stock disponible"

Usuario mapea:
```json
{
  "FORMATO DE COMO APUNTAR LAS COMPRAS": "name",
  "Precio $": "precio",
  "Stock disponible": "cantidad"
}
```

Y guarda como "Proveedor XYZ" para reutilizar en próximas importaciones.

## Comandos

```bash
# Aplicar migración
python scripts/py/bootstrap_imports.py --dir ops/migrations/2025-10-28_180_import_column_mappings

# Rollback
psql -U postgres -d gestiqclouddb_dev -f ops/migrations/2025-10-28_180_import_column_mappings/down.sql
```
