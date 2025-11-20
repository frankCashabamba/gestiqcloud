# 🚀 Guía de Configuración de Base de Datos - GestiQCloud v2.0

## 📋 TL;DR - Quick Start

```bash
# 1. Levantar PostgreSQL
docker-compose up -d db

# 2. Crear estructura completa
python scripts/init_database.py

# 3. Verificar
curl http://localhost:8000/api/v1/tenants

# ✅ LISTO
```

---

## 🎯 Objetivo

**Configurar la base de datos de forma profesional con UN SOLO comando.**

No más migraciones fragmentadas. Schema completo, reproducible, profesional.

---

## 🏗️ Arquitectura de Datos

### Entidad Principal: `Tenant` (UUID)

```
tenants (UUID PK) ← Entidad principal
  ├── products
  ├── clients
  ├── facturas
  ├── stock_items
  ├── bank_accounts
  ├── import_batches
  └── ... todas las tablas de negocio
```

### Legacy: `core_empresa` (INT PK)

Mantenida solo para **compatibilidad backward**.

```sql
-- ❌ EVITAR en nuevo código
SELECT * FROM core_empresa WHERE id = 1;

-- ✅ USAR siempre
SELECT * FROM tenants WHERE id = 'uuid-here';
```

---

## 📦 Estructura de Archivos

```
ops/schema/
├── complete_schema.sql          # ⭐ Schema completo (700+ líneas)
└── README.md                    # Documentación técnica

scripts/
├── init_database.py             # ⭐ Script de inicialización
└── migrate_old_to_new.py        # Migración desde sistema antiguo (futuro)

ops/migrations/                  # ⚠️ OBSOLETO (mantener solo para referencia)
└── README_DEPRECATED.md
```

---

## 🚀 Métodos de Instalación

### Método 1: Script Python (RECOMENDADO)

```bash
# Desarrollo local - Drop + Create automático
python scripts/init_database.py

# Con confirmación manual
python scripts/init_database.py --confirm

# Sin crear tenant/productos demo
python scripts/init_database.py --no-demo

# Producción (requiere escribir "BORRAR TODO")
python scripts/init_database.py --env production
```

**Output esperado:**
```
============================================================
  GESTIQCLOUD - Inicialización de Base de Datos
============================================================

⚠️  ADVERTENCIA: Este script ELIMINARÁ TODOS LOS DATOS
⚠️  Solo usar en desarrollo o con backup completo

📊 Conectando a: localhost:5432/gestiqclouddb_dev

🗑️  Eliminando schema existente...
   ✓ Todas las tablas eliminadas

📄 Ejecutando schema: complete_schema.sql
   ✓ Schema creado exitosamente

🔍 Verificando instalación...
   ✓ Tablas creadas: 52
   ✓ Todas las tablas críticas presentes
   ✓ Tipos de empresa: 4
   ✓ Roles base: 4
   ✓ Extensiones: uuid-ossp, pg_trgm

🏢 Creando tenant demo...
   ✓ Tenant creado: Empresa Demo (abc-123-uuid)
   ✓ 3 productos demo creados

============================================================
  ✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE
============================================================

📌 Próximos pasos:
   1. Reinicia el backend: docker-compose restart backend
   2. Verifica con: http://localhost:8000/docs
   3. Crea tu primer tenant via API o admin panel
```

### Método 2: psql directo

```bash
# Drop + Create database
dropdb -U postgres gestiqclouddb_dev
createdb -U postgres gestiqclouddb_dev

# Aplicar schema
psql -U postgres -d gestiqclouddb_dev -f ops/schema/complete_schema.sql
```

### Método 3: Docker

```bash
# Recrear contenedor DB desde cero
docker-compose down -v
docker-compose up -d db

# Esperar inicio
sleep 5

# Aplicar schema
cat ops/schema/complete_schema.sql | docker exec -i db psql -U postgres -d gestiqclouddb_dev
```

---

## 🔍 Verificación Post-Instalación

### 1. Verificar tablas creadas

```sql
-- Contar tablas
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Esperado: ~52 tablas
```

### 2. Verificar seed data

```sql
-- Tipos de empresa
SELECT * FROM core_tipoempresa;
-- 4 registros: Autónomo, SL, SA, Cooperativa

-- Roles base
SELECT * FROM core_rolbase;
-- 4 registros: Owner, Manager, Cashier, Accountant

-- Monedas
SELECT * FROM core_moneda;
-- 2 registros: EUR, USD
```

### 3. Verificar tenant demo (si se creó)

```sql
SELECT id, nombre, country_code, base_currency FROM tenants;
-- 1 registro: Empresa Demo

SELECT id, name, sku, price FROM products;
-- 3 productos demo
```

### 4. Verificar extensiones

```sql
SELECT extname FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pg_trgm');
-- 2 extensiones
```

### 5. Verificar índices

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'products';

-- Esperado:
-- products_pkey (PRIMARY KEY)
-- idx_products_tenant
-- idx_products_sku
-- idx_products_name (GIN index para búsqueda fuzzy)
```

---

## 🧪 Testing de Estructura

### Test 1: Crear tenant

```python
import uuid
from sqlalchemy import text

tenant_id = uuid.uuid4()
db.execute(text("""
    INSERT INTO tenants (id, nombre, country_code, base_currency)
    VALUES (:id, :nombre, :country, :currency)
"""), {
    "id": str(tenant_id),
    "nombre": "Mi Empresa SL",
    "country": "ES",
    "currency": "EUR"
})
db.commit()
# ✅ Debe funcionar sin errores
```

### Test 2: Crear producto con tenant

```python
db.execute(text("""
    INSERT INTO products (tenant_id, name, sku, price, stock)
    VALUES (:tid, 'Producto Test', 'TEST-001', 19.99, 100)
"""), {"tid": str(tenant_id)})
db.commit()
# ✅ Debe funcionar
```

### Test 3: RLS (Row Level Security)

```python
# Configurar tenant en sesión
db.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})

# Query con RLS activo
products = db.execute(text("SELECT * FROM products")).fetchall()
# ✅ Solo debe retornar productos del tenant actual
```

---

## 🔐 Configuración de Seguridad

### Variables de Entorno

```bash
# .env para desarrollo
DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev

# .env para producción
DB_DSN=postgresql://user:password@db.example.com:5432/gestiqcloud_prod
```

### Usuarios PostgreSQL

```sql
-- Crear usuario de aplicación (producción)
CREATE USER gestiqcloud_app WITH PASSWORD 'secure-password-here';

-- Permisos básicos
GRANT CONNECT ON DATABASE gestiqclouddb_prod TO gestiqcloud_app;
GRANT USAGE ON SCHEMA public TO gestiqcloud_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gestiqcloud_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gestiqcloud_app;

-- RLS requiere bypassrls o políticas específicas
ALTER USER gestiqcloud_app WITH BYPASSRLS;  -- Solo si backend gestiona RLS
```

---

## 📊 Schema Overview

### Tablas por Categoría (52 total)

#### Core Multi-Tenant (6)
- `tenants` ⭐ Principal
- `products`, `product_categories`
- `clients`
- `warehouses`
- `stock_items`, `stock_moves`

#### Facturación (6)
- `facturas`, `invoice_line`
- `facturas_temp`
- `bank_accounts`, `bank_transactions`
- `payments`, `internal_transfers`

#### E-Facturación (4)
- `einvoicing_credentials`
- `sri_submissions`
- `sii_batches`, `sii_batch_items`

#### Importaciones (8)
- `import_batches`, `import_items`
- `import_item_corrections`
- `import_attachments`
- `import_mappings`
- `import_lineage`
- `import_ocr_jobs`
- `auditoria_importacion`

#### Auth & Usuarios (7)
- `auth_user`
- `usuarios_usuarioempresa`
- `core_rolempresa`, `usuario_rolempresa`
- `core_perfilusuario`
- `auth_refresh_family`, `auth_refresh_token`
- `auth_audit_log`

#### Legacy (14 - Compatibilidad)
- `core_empresa` ⚠️ DEPRECADO
- `core_tipoempresa`, `core_tiponegocio`
- `core_idioma`, `core_moneda`, `core_dia`
- `core_rolbase`, `core_categoriaempresa`
- ... etc

#### Recetas (2)
- `recipes`, `recipe_ingredients`

---

## 🔄 Migración desde Sistema Antiguo

Si ya tienes datos en migraciones antiguas:

### Paso 1: Backup completo

```bash
pg_dump -U postgres -d gestiqclouddb_dev -F c -f backup_old_system.pgcustom
```

### Paso 2: Aplicar nuevo schema

```bash
python scripts/init_database.py --no-demo
```

### Paso 3: Restaurar datos (manual)

```python
# Ejemplo: Migrar tenants desde core_empresa
old_empresas = old_db.execute("SELECT * FROM core_empresa").fetchall()

for emp in old_empresas:
    new_db.execute("""
        INSERT INTO tenants (
            nombre, ruc, country_code, base_currency,
            telefono, ciudad, activo
        ) VALUES (
            :nombre, :ruc, :country, :currency,
            :telefono, :ciudad, :activo
        )
    """, {
        "nombre": emp.nombre,
        "ruc": emp.ruc,
        "country": emp.pais[:2] if emp.pais else "ES",
        "currency": "EUR" if emp.pais == "España" else "USD",
        "telefono": emp.telefono,
        "ciudad": emp.ciudad,
        "activo": emp.activo
    })
```

---

## 🚨 Troubleshooting

### Error: `relation "tenants" does not exist`

**Causa**: Schema no aplicado
**Solución**:
```bash
python scripts/init_database.py
```

### Error: `permission denied for table tenants`

**Causa**: Usuario sin permisos
**Solución**:
```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```

### Error: `duplicate key value violates unique constraint`

**Causa**: Datos duplicados en migración
**Solución**:
```bash
# Drop y recrear limpio
python scripts/init_database.py --confirm
```

### Error: `database "gestiqclouddb_dev" does not exist`

**Causa**: DB no creada
**Solución**:
```bash
createdb -U postgres gestiqclouddb_dev
python scripts/init_database.py
```

---

## 📚 Referencias

- [complete_schema.sql](ops/schema/complete_schema.sql) - Schema SQL completo
- [init_database.py](scripts/init_database.py) - Script de inicialización
- [ops/schema/README.md](ops/schema/README.md) - Documentación técnica
- [AGENTS.md](AGENTS.md) - Arquitectura del sistema

---

## ✅ Checklist Pre-Producción

Antes de deploy en producción:

- [ ] Backup completo de datos existentes
- [ ] Revisar schema SQL línea por línea
- [ ] Probar en ambiente staging primero
- [ ] Configurar usuario de aplicación con permisos mínimos
- [ ] Habilitar SSL en conexión DB
- [ ] Configurar RLS correctamente
- [ ] Migrar datos legacy si aplica
- [ ] Testing completo de endpoints críticos
- [ ] Monitoreo de performance post-migración
- [ ] Plan de rollback documentado

---

**Versión**: 2.0
**Última actualización**: 26 Enero 2025
**Estado**: ✅ PRODUCTION READY
