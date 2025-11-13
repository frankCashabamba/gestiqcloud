# Migración UUID Completa - 2025-10-26

## Descripción

Esta migración convierte **todas las Primary Keys principales** de `integer` a `UUID` para lograr consistencia arquitectónica completa en el sistema multi-tenant.

## Alcance

### Tablas Migradas

| Tabla | PK Original | PK Nueva | Impacto |
|-------|-------------|----------|---------|
| `clients` | int | **UUID** | ✅ Alto |
| `products` | int | **UUID** | ✅ Alto |
| `facturas` | int | **UUID** | ✅ Crítico |
| `invoice_line` | int | **UUID** | ✅ Medio |
| `bank_accounts` | int | **UUID** | ✅ Alto |
| `bank_transactions` | int | **UUID** | ✅ Alto |
| `payments` | int | **UUID** | ✅ Medio |
| `internal_transfers` | int | **UUID** | ✅ Bajo |
| `facturas_temp` | int | **UUID** | ✅ Bajo |
| `recipes` | int | **UUID** | ✅ Bajo |
| `recipe_ingredients` | int | **UUID** | ✅ Bajo |

### Foreign Keys Actualizadas

Total: **25+ Foreign Keys** migradas de int a UUID

### Constraint Renombrado

- `modulos_moduloasignado_usuario_id_modulo_id_empresa_id_uniq` → 
- `modulos_moduloasignado_usuario_id_modulo_id_tenant_id_uniq`

## Pre-requisitos

⚠️ **CRÍTICO**: Esta migración es **IRREVERSIBLE** y puede tomar varios minutos en bases de datos grandes.

### Antes de Ejecutar

1. **Backup completo de la base de datos:**
   ```bash
   pg_dump -U postgres gestiqclouddb > backup_pre_uuid_$(date +%Y%m%d).sql
   ```

2. **Verificar espacio en disco:** Aproximadamente 2x el tamaño de las tablas afectadas

3. **Planificar ventana de mantenimiento:** Estimado 5-15 minutos (depende del volumen)

4. **Detener aplicación:** Evitar escrituras durante la migración

## Ejecución

```bash
# 1. Backup
pg_dump -U postgres gestiqclouddb > backup_pre_uuid.sql

# 2. Aplicar migración
psql -U postgres -d gestiqclouddb -f ops/migrations/2025-10-26_200_uuid_complete_migration/up.sql

# 3. Verificar
psql -U postgres -d gestiqclouddb -c "
  SELECT table_name, column_name, data_type 
  FROM information_schema.columns 
  WHERE column_name LIKE '%_id' 
    AND table_name IN ('clients', 'products', 'facturas')
  ORDER BY table_name;
"
```

## Validación Post-Migración

### 1. Verificar PKs UUID
```sql
SELECT 
    t.table_name, 
    k.column_name, 
    c.data_type
FROM information_schema.table_constraints t
JOIN information_schema.key_column_usage k 
  ON t.constraint_name = k.constraint_name
JOIN information_schema.columns c 
  ON k.table_name = c.table_name 
  AND k.column_name = c.column_name
WHERE t.constraint_type = 'PRIMARY KEY'
  AND c.table_schema = 'public'
  AND t.table_name IN (
    'clients', 'products', 'facturas', 
    'bank_accounts', 'bank_transactions'
  );
```

**Resultado esperado:** Todas deben ser `uuid`

### 2. Verificar FKs
```sql
SELECT 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    c.data_type
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.columns c 
  ON kcu.table_name = c.table_name 
  AND kcu.column_name = c.column_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND kcu.column_name IN ('cliente_id', 'factura_id', 'product_id')
ORDER BY tc.table_name;
```

### 3. Contar Registros (Integridad)
```sql
-- Antes y después deben coincidir
SELECT 
    'clients' AS tabla, COUNT(*) AS registros FROM clients
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'facturas', COUNT(*) FROM facturas
UNION ALL
SELECT 'invoice_line', COUNT(*) FROM invoice_line;
```

### 4. Test Funcional
```bash
# Ejecutar test suite completo
cd apps/backend
pytest app/tests/ -v
```

## Rollback

⚠️ **NO SOPORTADO** - Esta migración es irreversible.

En caso de problemas críticos:
1. Restaurar desde backup:
   ```bash
   dropdb gestiqclouddb
   createdb gestiqclouddb
   psql -U postgres -d gestiqclouddb < backup_pre_uuid.sql
   ```

## Tiempo Estimado

| Volumen de Datos | Tiempo Estimado |
|------------------|-----------------|
| < 10K registros | 2-5 minutos |
| 10K - 100K | 5-10 minutos |
| 100K - 1M | 10-30 minutos |
| > 1M | 30+ minutos |

## Impacto en el Código

### Cambios en Modelos

✅ **Ya realizados** en commit actual:
- `app/models/core/clients.py`
- `app/models/core/products.py`
- `app/models/core/facturacion.py`
- `app/models/core/invoiceLine.py`
- `app/models/core/einvoicing.py`
- `app/modules/proveedores/infrastructure/models.py`

### APIs Afectadas

Todos los endpoints que devuelven IDs ahora devolverán UUIDs:

```json
// ANTES
{
  "id": 123,
  "cliente_id": 456
}

// DESPUÉS
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "cliente_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

⚠️ **Actualizar clientes frontend** para manejar UUIDs en lugar de integers.

## Changelog

### Archivos Modificados
- `apps/backend/app/models/core/clients.py` - Migrado Cliente.id → UUID
- `apps/backend/app/models/core/products.py` - Migrado Product/Recipe/RecipeIngredient → UUID
- `apps/backend/app/models/core/facturacion.py` - Migrado Invoice/BankAccount/BankTransaction/Payment → UUID
- `apps/backend/app/models/core/invoiceLine.py` - Migrado LineaFactura/LineaPanaderia/LineaTaller → UUID
- `apps/backend/app/models/core/einvoicing.py` - Actualizado SRISubmission.invoice_id y SIIBatchItem.invoice_id → UUID
- `apps/backend/app/models/core/modulo.py` - Renombrado constraint empresa_id → tenant_id
- `apps/backend/app/modules/proveedores/infrastructure/models.py` - Migrado Proveedor/ProveedorContact/ProveedorAddress → UUID

## Beneficios Post-Migración

✅ **Consistencia arquitectónica:** 100% UUID en PKs principales  
✅ **Multi-tenant sólido:** Todas las FKs alineadas con tenants.id (UUID)  
✅ **Escalabilidad:** UUIDs permiten generación distribuida sin colisiones  
✅ **Seguridad:** IDs no secuenciales (no predictibles)  
✅ **Interoperabilidad:** Estándar RFC 4122

## Soporte

**Equipo:** GestiQCloud Backend Team  
**Contacto:** [Slack #backend-migrations]  
**Documentación:** MODELS_UUID_MIGRATION_ANALYSIS.md
