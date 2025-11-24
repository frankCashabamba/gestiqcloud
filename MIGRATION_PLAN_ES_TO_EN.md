# Plan de Migración: Español → Inglés (Completitud)

## Resumen Ejecutivo
- **Alcance**: Eliminar todos los restos en español en modelos, base de datos, índices, constraints y enums
- **Fases**: 4 fases principales (1 semana cada una)
- **Riesgo**: ALTO (impacta modelos, DB, tests, y toda la aplicación)

---

## FASE 1: Audit & Validación (Días 1-2)

### 1.1 Escanear todo el código base
```bash
# En backend/app
grep -r "class.*Empresa\|class.*Rol\|class.*Nomina\|class.*Caja\|class.*Facturacion" --include="*.py"
grep -r "idx_.*_en[s]?paño\|uq_empresa_\|fk_.*empresa" --include="*.py" --include="*.sql"
grep -r "\"tipo\"|\"severidad\"|\"estado\"|\"descripcion\"" --include="*.py" # en enums españoles
grep -r "class.*Empresa\|class.*Usuario.*Rol\|class.*Modulo" app/models/ --include="*.py"
```

### 1.2 Base de datos - Buscar restos
```sql
-- Listar tablas con nombres en español (aún existen?)
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
AND table_name IN (
  'empresa', 'empresas', 'usuarios_usuarioempresa',
  'usuarios_usuariorolempresa', 'modulos_*',
  'facturacion_*', 'plan_cuentas_*', 'nomina_*', 'caja_*'
);

-- Indices en español
SELECT indexname FROM pg_indexes
WHERE indexdef LIKE '%idx_%_%_en%' OR indexname LIKE 'uq_empresa_%'
  OR indexdef LIKE '%idx_incidents_severidad%';

-- Constraints en español
SELECT constraint_name FROM information_schema.table_constraints
WHERE constraint_name LIKE 'uq_empresa_%' OR constraint_name LIKE 'fk_%empresa%';
```

### 1.3 Enums en código fuente (scan)
- `caja_movimiento_tipo` (VENTA, COMPRA, BANCO)
- `caja_movimiento_categoria`
- `cierre_caja_status`
- `movimientoestado`
- `movimientotipo`
- `nomina_status`
- `nomina_tipo`

### 1.4 Documentación de hallazgos
Crear `INVENTORY_SPANISH_REMNANTS.md` con lista detallada de:
- Módulos/carpetas en español
- Nombres de clase con alias españoles
- Campos/columnas con nombres españoles
- Enums con valores españoles
- Índices/constraints en español
- Tests que referencian nombres españoles

---

## FASE 2: Refactorización de Código Python (Días 3-5)

### 2.1 Renombrar Módulos/Carpetas
**Orden de ejecución**:
1. `app/models/empresa/` → `app/models/company/`
   - `empresa.py` → `company.py`
   - `usuarioempresa.py` → `user_company.py`
   - `rolempresas.py` → `company_role.py`
   - `usuario_rolempresa.py` → `user_company_role.py`
   - `settings.py` → `company_settings.py` (si aplica)

2. `app/models/core/facturacion.py` → `app/models/billing/billing.py`
3. `app/models/core/plan_cuentas.py` → `app/models/accounting/chart_of_accounts.py`
4. `app/models/core/modulo.py` → `app/models/platform/module.py` (o `system/`)
5. `app/models/hr/nomina.py` → `app/models/hr/payroll.py`
6. `app/models/finance/caja.py` → `app/models/finance/cash_management.py`

### 2.2 Renombrar Clases & Enums
En cada archivo:
- `Empresa` → `Company`
- `UsuarioEmpresa` → `UserCompany`
- `RolEmpresa` → `CompanyRole`
- `UsuarioRolEmpresa` → `UserCompanyRole`
- `Facturacion` → `Billing`
- `PlanCuentas` → `ChartOfAccounts`
- `Modulo` → `Module`
- `Nomina` → `Payroll`
- `Caja` → `CashManagement`
- `TipoEmpresa` → `CompanyType`
- `TipoNegocio` → `BusinessCategory`

Enums:
- `caja_movimiento_tipo` → `cash_movement_type` (con valores SALE, PURCHASE, BANK)
- `caja_movimiento_categoria` → `cash_movement_category`
- `cierre_caja_status` → `cash_closing_status`
- `nomina_status` → `payroll_status` (ACTIVE, INACTIVE, ARCHIVED)
- `nomina_tipo` → `payroll_type` (SALARY, BONUS, etc.)

### 2.3 Renombrar Propiedades/Campos
Ejemplo en `company.py`:
```python
# Antes
class Empresa:
    nombre: str
    activo: bool
    tipo_empresa: TipoEmpresa

# Después
class Company:
    name: str
    is_active: bool
    company_type: CompanyType
```

### 2.4 Update de __init__.py y imports
- `from app.models.empresa import ...` → `from app.models.company import ...`
- `from app.models.core.facturacion import ...` → `from app.models.billing import ...`
- Escanear en `app/__init__.py`, `app/models/__init__.py`, etc.

### 2.5 Update de Routers/API routes
Buscar y actualizar:
```python
# Antes
from app.routers.empresa import router as empresa_router

# Después
from app.routers.company import router as company_router
```

### 2.6 Update de Services
- `app/services/empresa_service.py` → `app/services/company_service.py`
- `app/services/nomina_service.py` → `app/services/payroll_service.py`
- etc.

### 2.7 Update de Tests
- Renombrar archivos de test
- Update de imports en tests
- Update de fixtures y factory methods
- Buscar referencias a nombres españoles en assertions

---

## FASE 3: Migraciones de Base de Datos (Días 6-10)

### 3.1 Crear nueva migración Alembic
```bash
alembic revision -m "complete_spanish_to_english_migration"
```

### 3.2 Script de migración (008 o siguiente)
El script debe hacer:

#### A. Crear tablas nuevas (inglés)
```sql
-- 1. company (de empresa)
CREATE TABLE company AS SELECT * FROM empresa;

-- 2. user_company (de usuarios_usuarioempresa)
CREATE TABLE user_company AS SELECT * FROM usuarios_usuarioempresa;

-- 3. company_role (de rolempresas)
CREATE TABLE company_role AS SELECT * FROM rolempresas;

-- 4. user_company_role (de usuarios_usuariorolempresa)
CREATE TABLE user_company_role AS SELECT * FROM usuarios_usuariorolempresa;

-- 5. Para modulos
CREATE TABLE module AS SELECT * FROM modulos_modulo;
CREATE TABLE company_module AS SELECT * FROM modulos_empresamodulo;
CREATE TABLE assigned_module AS SELECT * FROM modulos_moduloasignado;

-- etc. para facturacion, nomina, caja, plan_cuentas
```

#### B. Renombrar columnas en tablas nuevas
```sql
-- company
ALTER TABLE company RENAME COLUMN id_empresa TO id;
ALTER TABLE company RENAME COLUMN nombre_empresa TO name;
ALTER TABLE company RENAME COLUMN razon_social TO legal_name;
-- ... etc
```

#### C. Recrear índices e constraints en inglés
```sql
-- Indices
CREATE INDEX idx_company_tenant_id ON company(tenant_id);
CREATE INDEX idx_company_code ON company(company_code);
-- ... etc

-- Constraints (foreign keys)
ALTER TABLE user_company ADD CONSTRAINT fk_user_company_user_id
  FOREIGN KEY (user_id) REFERENCES auth_user(id);
-- ... etc
```

#### D. Migración de datos
```sql
-- Si hay datos, mapear/transformar según sea necesario
INSERT INTO company
  SELECT id, nombre, descripcion, activo, created_at, updated_at, tenant_id
  FROM empresa;
```

#### E. Actualizar tablas dependientes
Cambiar foreign keys que apunten a las tablas viejas:
```sql
-- Si facturas tiene fk a empresa, cambiar a company
ALTER TABLE facturas DROP CONSTRAINT fk_facturas_empresa_id;
ALTER TABLE facturas RENAME COLUMN empresa_id TO company_id;
ALTER TABLE facturas ADD CONSTRAINT fk_facturas_company_id
  FOREIGN KEY (company_id) REFERENCES company(id);
```

#### F. Drop de tablas viejas (AL FINAL)
```sql
DROP TABLE IF EXISTS usuarios_usuariorolempresa CASCADE;
DROP TABLE IF EXISTS usuarios_usuarioempresa CASCADE;
DROP TABLE IF EXISTS rolempresas CASCADE;
DROP TABLE IF EXISTS empresa CASCADE;
-- ... etc
```

### 3.3 Actualizar ORM models en alembic env.py
Si necesario, asegurar que la configuración de SQLAlchemy apunta a los nuevos modelos.

### 3.4 Crear rollback migration
Crear una migración inversa para rollback en caso de problemas.

---

## FASE 4: Tests y Validación (Días 11-14)

### 4.1 Ejecutar tests
```bash
pytest tests/ -v --tb=short
```

### 4.2 Validar con script SQL
```bash
psql -U postgres -d proyecto_db -f ops/migrations/validate_migration.sql
```

### 4.3 Verificar integridad de datos
- Row counts antes y después
- Verificar FKs funcionan
- Verificar indices se crearon

### 4.4 Fix de tests fallidos
- Update de imports en test files
- Update de fixtures
- Update de factory methods

### 4.5 Fix de comentarios/docstrings
```python
# Antes
def crear_empresa():
    """Crea una empresa nueva"""

# Después
def create_company():
    """Creates a new company"""
```

---

## Checklist por Archivo

### Modelos (`app/models/`)
- [ ] `empresa/empresa.py` → renombreado y migrado
- [ ] `empresa/usuarioempresa.py` → renombreado y migrado
- [ ] `empresa/rolempresas.py` → renombreado y migrado
- [ ] `empresa/usuario_rolempresa.py` → renombreado y migrado
- [ ] `core/facturacion.py` → renombreado y migrado
- [ ] `core/plan_cuentas.py` → renombreado y migrado
- [ ] `core/modulo.py` → renombreado y migrado
- [ ] `hr/nomina.py` → renombreado y migrado
- [ ] `finance/caja.py` → renombreado y migrado
- [ ] `ai/incident.py` → renombreado campos españoles
- [ ] `pos/register.py`, `pos/doc_series.py`, `pos/receipt.py` → docstrings
- [ ] `core/document_line.py` → documentación
- [ ] `production/_production_order.py` → comentarios/campos

### Importaciones
- [ ] `app/__init__.py`
- [ ] `app/models/__init__.py`
- [ ] `app/routers/__init__.py`
- [ ] `app/services/__init__.py`
- [ ] `app/api/__init__.py`

### Routers/API
- [ ] `app/routers/empresa.py` → renombreado a `company.py`
- [ ] Actualizar imports en otros routers

### Services
- [ ] `app/services/empresa_service.py` → renombreado
- [ ] `app/services/nomina_service.py` → renombreado
- [ ] etc.

### Schemas (Pydantic)
- [ ] Buscar y renombrar todos los schemas
- [ ] Actualizar field_aliases si existen

### Tests
- [ ] `tests/test_empresa_module.py` → renombreado
- [ ] `tests/test_finance_caja.py` → renombreado
- [ ] Actualizar imports en todos los tests
- [ ] Actualizar fixtures

### Configuración
- [ ] `app/config/` - actualizar cualquier config relacionada
- [ ] `app/settings/` - actualizar settings

### Documentación
- [ ] Docstrings en español → inglés en todos los archivos modificados
- [ ] Comentarios en español → inglés
- [ ] Update de README/docs si existen

---

## Herramientas/Scripts Recomendados

### Script 1: Encontrar todos los restos
```bash
#!/bin/bash
echo "=== SPANISH CLASSES ==="
grep -r "class.*Empresa\|class.*Nomina\|class.*Caja" app/models/ --include="*.py"

echo -e "\n=== SPANISH ENUMS ==="
grep -r "caja_movimiento_\|nomina_\|cierre_caja_" app/models/ --include="*.py"

echo -e "\n=== SPANISH IMPORTS ==="
grep -r "from app.models.empresa\|from app.models.core.facturacion" app/ --include="*.py"

echo -e "\n=== SPANISH COMMENTS/DOCSTRINGS ==="
grep -r "\".*[áéíóú].*\"|'.*[áéíóú].*'" app/models/ --include="*.py" | head -20
```

### Script 2: Find & Replace helper
```bash
# Usar sed con cuidado
# Ejemplo: renombrar en todos los archivos
find app/ -name "*.py" -exec sed -i 's/from app.models.empresa import/from app.models.company import/g' {} \;
```

### Script 3: Validar migración
Usar el `validate_migration.sql` existente, pero actualizarlo con:
- Nuevas tablas en inglés
- Nuevos índices en inglés
- Nuevos constraints en inglés

---

## Riesgos y Mitigación

| Riesgo | Severidad | Mitigación |
|--------|-----------|-----------|
| Romper datos existentes | CRÍTICA | Backup completo de BD antes de migración |
| Imports rotos | ALTA | Crear mapping table de renames antes de hacer cambios |
| Tests fallidos | MEDIA | Actualizar tests en paralelo |
| Inconsistencias en BD | MEDIA | Validar con script SQL después de migración |
| Duplicados en código | MEDIA | Usar git diff para revisar todos los cambios |

---

## Estimación de Esfuerzo
- **Audit**: 4 horas
- **Refactor código**: 16-20 horas (depende de cantidad de archivos)
- **Migrations DB**: 8-10 horas
- **Tests y validación**: 8-12 horas
- **Buffer/fixes**: 10 horas

**Total**: 46-56 horas (1-1.5 semanas)

---

## Próximo Paso
¿Quieres que empecemos por:
1. **Audit completo** - escanear todo y generar inventario
2. **Script de búsqueda** - automatizar búsqueda de restos
3. **Migración DB** - crear scripts SQL
4. **Refactor de modelos** - empezar por renombrar clases
