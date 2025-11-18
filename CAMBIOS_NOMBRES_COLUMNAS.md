# Cambios de Nombres de Columnas - Resumen

## Descripción
Se han realizado cambios para alinear los nombres de columnas en los modelos SQLAlchemy con los nombres esperados por el código existente (principalmente en español).

## Cambios Realizados

### 1. Modelo: `CompanyUser` (`usuarioempresa.py`)
**Columnas renombradas:**
- `active` → `activo`
- `is_admin` → `es_admin_empresa`

**Propiedades de compatibilidad añadidas (alias en inglés):**
- `is_admin` → propiedad que devuelve `es_admin_empresa`
- `active` → propiedad que devuelve `activo`

### 2. Modelo: `CompanyUserRole` (`usuario_rolempresa.py`)
**Columnas renombradas:**
- `user_id` → `usuario_id`
- `role_id` → `rol_id`
- `active` → `activo`

**Propiedades de compatibilidad añadidas (alias en inglés):**
- `user_id` → propiedad que devuelve `usuario_id`
- `role_id` → propiedad que devuelve `rol_id`
- `active` → propiedad que devuelve `activo`

### 3. Modelo: `Sale` (`venta.py`)
**Columnas renombradas:**
- `customer_id` → `cliente_id`
- `date` → `fecha`
- `status` → `estado`
- `notes` → `notas`
- `user_id` → `usuario_id`

**Relaciones renombradas:**
- `customer` → `cliente`

**Propiedades de compatibilidad añadidas (alias en inglés):**
- `customer_id` → propiedad que devuelve `cliente_id`
- `date` → propiedad que devuelve `fecha`
- `status` → propiedad que devuelve `estado`
- `notes` → propiedad que devuelve `notas`
- `user_id` → propiedad que devuelve `usuario_id`
- `customer` → propiedad que devuelve `cliente`

### 4. Repositorio: `usuarios/repositories.py`
**Actualizadas referencias a campos en consultas:**
- `CompanyUser.is_admin` → `CompanyUser.es_admin_empresa`
- `CompanyUser.active` → `CompanyUser.activo`
- `CompanyUserRole.user_id` → `CompanyUserRole.usuario_id`
- `CompanyUserRole.role_id` → `CompanyUserRole.rol_id`
- `CompanyUserRole.active` → `CompanyUserRole.activo`

**Método `insert_usuario_empresa()` actualizado:**
- Parámetros de inicialización de `CompanyUser` actualizados para usar nombres en español

### 5. Test: `test_repo_ventas_compat.py`
**Actualizados parámetros de llamada a `repo.create()` y `repo.update()`:**
- `date=` → `fecha=`
- `customer_id=` → `cliente_id=`
- `status=` → `estado=`
- Acceso a propiedades: `v.date` → `v.fecha`, `v.status` → `v.estado`, etc.

## Notas Importantes

1. **Migraciones de Base de Datos**: Los cambios de nombres de columnas requieren migraciones de Alembic. Las migraciones actuales están vacías (004, 003, 002_rolempresas_english). Estas necesitan ser actualizadas o creadas nuevas migraciones si la base de datos tiene datos existentes.

2. **Propiedades de Compatibilidad**: Se han añadido propiedades en inglés como alias para mantener compatibilidad con código que usa nombres en inglés. Estas son propiedades de solo lectura (en su mayoría).

3. **Modelos Afectados**: Los cambios afectan principalmente a:
   - `app/models/empresa/usuarioempresa.py`
   - `app/models/empresa/usuario_rolempresa.py`
   - `app/models/sales/venta.py`

4. **Repositorios Actualizados**:
   - `app/modules/usuarios/infrastructure/repositories.py`

5. **Tests Actualizados**:
   - `app/tests/test_repo_ventas_compat.py`

## Próximos Pasos

1. Ejecutar las pruebas para verificar que los cambios funcionan correctamente
2. Si hay errores 404 en rutas, verificar que los routers estén registrados correctamente
3. Actualizar migraciones de base de datos si es necesario
4. Buscar y actualizar cualquier otro código que use los nombres antiguos en inglés
