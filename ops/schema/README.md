# Schema Completo - GestiQCloud v2.0

## 📋 Descripción

Este directorio contiene el **schema completo y definitivo** de la base de datos.

En lugar de migraciones incrementales, usamos un único archivo SQL que define TODA la estructura.

## 📦 Archivos

- **`complete_schema.sql`** - Schema completo (700+ líneas)
  - Todas las tablas con relaciones correctas
  - Índices optimizados
  - Triggers y funciones
  - RLS policies
  - Seed data inicial

## 🚀 Uso

### Opción 1: Script Python (RECOMENDADO)

```bash
# Desarrollo local (sin confirmación)
python scripts/init_database.py

# Con confirmación manual
python scripts/init_database.py --confirm

# Sin datos demo
python scripts/init_database.py --no-demo

# Producción (doble confirmación)
python scripts/init_database.py --env production
```

### Opción 2: psql directo

```bash
# 1. Drop database completa
dropdb gestiqclouddb_dev
createdb gestiqclouddb_dev

# 2. Ejecutar schema
psql -U postgres -d gestiqclouddb_dev -f ops/schema/complete_schema.sql
```

### Opción 3: Docker

```bash
# Recrear contenedor DB desde cero
docker-compose down -v
docker-compose up -d db

# Esperar a que esté listo
sleep 5

# Aplicar schema
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/schema/complete_schema.sql
```

## 🏗️ Estructura del Schema

### Orden de Creación

1. **Extensions** - uuid-ossp, pg_trgm
2. **Enums** - Tipos personalizados (movimiento_tipo, import_status, etc.)
3. **Tablas Core** - Sin dependencias (core_tipoempresa, core_moneda, etc.)
4. **Tabla Tenant** - Entidad principal UUID
5. **Tablas Dependientes** - products, clients, facturas, etc.
6. **Índices** - Performance optimization
7. **Triggers** - updated_at automático
8. **RLS Policies** - Tenant isolation
9. **Seed Data** - Datos iniciales (tipos, roles, idiomas)

### Tablas Principales (50+)

#### Multi-Tenant Core
- `tenants` ⭐ Entidad principal
- `products`, `product_categories`
- `clients`
- `stock_items`, `stock_moves`, `warehouses`

#### Facturación
- `facturas`, `invoice_line`
- `bank_accounts`, `bank_transactions`
- `payments`, `internal_transfers`

#### E-Facturación
- `einvoicing_credentials`
- `sri_submissions` (Ecuador)
- `sii_batches`, `sii_batch_items` (España)

#### Importaciones
- `import_batches`
- `import_items`
- `import_item_corrections`
- `import_attachments`
- `import_mappings`

#### Auth & Usuarios
- `auth_user` (superusuarios)
- `usuarios_usuarioempresa`
- `auth_refresh_family`, `auth_refresh_token`
- `auth_audit_log`

#### Legacy (Compatibilidad)
- `core_empresa` ⚠️ DEPRECADO
- `core_perfilusuario`
- `core_rolempresa`

## 🔍 Verificación Post-Instalación

```sql
-- Contar tablas creadas
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Esperado: ~50 tablas

-- Verificar tenant demo
SELECT id, nombre, country_code, base_currency FROM tenants;

-- Verificar productos demo
SELECT id, name, sku, price FROM products LIMIT 5;

-- Verificar seed data
SELECT COUNT(*) FROM core_tipoempresa;  -- 4 tipos
SELECT COUNT(*) FROM core_rolbase;      -- 4 roles
SELECT COUNT(*) FROM core_moneda;       -- 2 monedas

-- Verificar índices
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename;
```

## 📊 Seed Data Incluido

### Tipos de Empresa
- Autónomo
- SL (Sociedad Limitada)
- SA (Sociedad Anónima)
- Cooperativa

### Tipos de Negocio
- Retail/Bazar
- Panadería
- Taller Mecánico
- Restaurante
- Consultoría

### Roles Base
- Owner (acceso total)
- Manager (gestión operativa)
- Cashier (POS)
- Accountant (contabilidad)

### Idiomas
- Español (es)
- English (en)
- Català (ca)

### Monedas
- EUR (Euro)
- USD (Dólar)

## 🔐 Row Level Security (RLS)

El schema incluye políticas RLS básicas en tablas multi-tenant:

```sql
-- Habilitado en:
- tenants
- products
- stock_items, stock_moves
- clients
- facturas
- import_batches

-- Política aplicada:
CREATE POLICY tenant_isolation ON <table>
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));
```

Para usar RLS, el backend debe establecer:
```python
# En middleware FastAPI
await db.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
```

## 🧹 Limpieza de Migraciones Antiguas

Las migraciones en `ops/migrations/` quedan **OBSOLETAS**.

Este schema las reemplaza completamente. Solo mantener para referencia histórica.

```bash
# Opcional: Mover migraciones antiguas a archivo
mkdir ops/migrations_deprecated
mv ops/migrations/2025-* ops/migrations_deprecated/
```

## 🆚 Ventajas vs Migraciones Incrementales

| Aspecto | Migraciones Incrementales | Schema Completo |
|---------|---------------------------|-----------------|
| Complejidad | Alta (N archivos) | Baja (1 archivo) |
| Debugging | Difícil | Fácil |
| Reproducibilidad | Media | Alta |
| Onboarding | Lento | Rápido |
| Testing | Complejo | Simple |
| Estado conocido | Variable | Siempre igual |

## 🚨 Advertencias

1. **DESTRUCTIVO**: Borra TODOS los datos existentes
2. **Solo desarrollo**: No usar en producción con datos reales sin backup
3. **Idempotencia**: Es seguro ejecutar múltiples veces (DROP + CREATE)
4. **Compatibilidad**: Requiere PostgreSQL 15+

## 📅 Migración desde Sistema Antiguo

Si tienes datos en el sistema antiguo con migraciones:

```bash
# 1. Backup completo
pg_dump -U postgres gestiqclouddb_dev -F c -f backup_old_system.pgcustom

# 2. Aplicar nuevo schema
python scripts/init_database.py --no-demo

# 3. Migrar datos (script personalizado)
python scripts/migrate_old_to_new.py --backup backup_old_system.pgcustom
```

## 📚 Referencias

- [complete_schema.sql](./complete_schema.sql) - Schema SQL completo
- [../../scripts/init_database.py](../../scripts/init_database.py) - Script de inicialización
- [../../AGENTS.md](../../AGENTS.md) - Arquitectura del sistema

---

**Versión**: 2.0  
**Última actualización**: 26 Enero 2025  
**Compatibilidad**: PostgreSQL 15+
