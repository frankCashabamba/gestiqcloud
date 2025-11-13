# FRESH START - RESET COMPLETO A INGLÉS

## ⚠️ ADVERTENCIA
Este proceso **BORRA TODOS LOS DATOS** excepto:
- `auth_user`
- `modulos_modulo`
- `modulos_empresamodulo`
- `modulos_moduloasignado`

## Pasos

### 1. Backup Completo (YA HECHO)
```bash
✅ backup_before_english_20251101.sql (1.1 MB)
```

### 2. Backup Tablas Críticas
```bash
type backup_critical_tables.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev
```

**Verificar**:
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT * FROM backup_temp.auth_user LIMIT 1;"
```

### 3. DROP Todas las Tablas (excepto críticas)
```bash
type drop_all_except_critical.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev
```

**Verificar tablas restantes**:
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

Deberías ver solo:
- auth_user
- modulos_modulo
- modulos_empresamodulo
- modulos_moduloasignado
- schema_migrations

### 4. Crear Esquema Moderno
```bash
type create_modern_schema.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev
```

**Verificar esquema**:
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d products"
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d tenants"
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d stock_items"
```

Deberías ver columnas en INGLÉS:
- products: `name`, `sku`, `price`, `cost_price`, `description`
- tenants: `name`, `tax_id`, `phone`, `address`, `city`, `state`
- stock_items: `qty`, `location`, `lot`

### 5. Limpiar Backup Temporal
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "DROP SCHEMA backup_temp CASCADE;"
```

## Resultado

✅ **Base de datos limpia con:**
- Schema 100% inglés
- Sin duplicaciones
- Sin legacy
- auth_user intacto
- modulos_* intactos

## Rollback

Si necesitas volver atrás:
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -i db psql -U postgres gestiqclouddb_dev < backup_before_english_20251101.sql
```

## Siguiente Paso

Actualizar Models backend y Frontend para usar nombres en inglés.
