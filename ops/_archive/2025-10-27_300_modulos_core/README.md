# Migración 2025-10-27_300: Módulos Core ERP/CRM

## Objetivo

Crear las tablas necesarias para los módulos core del sistema ERP/CRM que ya tienen código pero les faltaban las migraciones SQL.

## Módulos Incluidos

### 1. Ventas
- **Tabla**: `ventas`
- **Propósito**: Pedidos de venta (pre-factura)
- **RLS**: ✅ Habilitado

### 2. Proveedores
- **Tablas**: `proveedores`, `proveedor_contactos`, `proveedor_direcciones`
- **Propósito**: Gestión de proveedores
- **RLS**: ✅ Habilitado

### 3. Compras
- **Tablas**: `compras`, `compra_lineas`
- **Propósito**: Órdenes de compra
- **RLS**: ✅ Habilitado

### 4. Gastos
- **Tabla**: `gastos`
- **Propósito**: Registro de gastos operativos
- **RLS**: ✅ Habilitado

### 5. Finanzas
- **Tablas**: `caja_movimientos`, `banco_movimientos`
- **Propósito**: Control de caja y conciliación bancaria
- **RLS**: ✅ Habilitado

### 6. RRHH
- **Tablas**: `empleados`, `vacaciones`
- **Propósito**: Gestión de recursos humanos
- **RLS**: ✅ Habilitado

### 7. Settings
- **Tabla**: `tenant_settings`
- **Propósito**: Configuración por tenant
- **RLS**: ✅ Habilitado

## Características

- ✅ RLS habilitado en todas las tablas multi-tenant
- ✅ Índices optimizados para queries comunes
- ✅ Constraints de integridad
- ✅ Triggers `updated_at` automáticos
- ✅ Valores por defecto apropiados
- ✅ Comentarios SQL descriptivos

## Verificación Post-Migración

```sql
-- Verificar que todas las tablas se crearon
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
  'ventas', 'proveedores', 'proveedor_contactos', 'proveedor_direcciones',
  'compras', 'compra_lineas', 'gastos', 'caja_movimientos',
  'banco_movimientos', 'empleados', 'vacaciones', 'tenant_settings'
)
ORDER BY tablename;

-- Verificar RLS
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('ventas', 'compras', 'gastos', 'empleados');

-- Verificar triggers
SELECT tgname, tgrelid::regclass
FROM pg_trigger
WHERE tgname LIKE 'update_%_updated_at';
```

## Impacto

- **Breaking Changes**: ❌ No
- **Requiere Downtime**: ❌ No
- **Reversible**: ✅ Sí (down.sql)

## Próximos Pasos

1. Crear modelos SQLAlchemy en `app/models/` para cada módulo
2. Eliminar modelos duplicados de `app/modules/*/infrastructure/models.py`
3. Actualizar repositorios para usar modelos centralizados
4. Crear endpoints REST para cada módulo
5. Añadir tests

## Dependencias

- Requiere migración `2025-10-26_000_baseline` (tenants, auth_user, etc.)
- Requiere tabla `products` para FKs
- Requiere tabla `clients` para FKs

## Notas

- Campo `usuario_id` es UUID string (no FK) para compatibilidad SQLite en tests
- `tenant_settings` usa JSONB para configuración flexible
- Estados de workflow están validados con CHECKs
