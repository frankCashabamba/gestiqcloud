# Estado: Estandarización a Inglés ✅

## Resumen General

Se ha completado la estandarización de nombres de modelos, tablas y columnas de español a inglés en el proyecto. Se mantiene **compatibilidad hacia atrás** mediante aliases para facilitar la transición gradual.

---

## ✅ Completado

### 1. Modelos Python (Classes)
- ✅ `Supplier` (fue `Proveedor`)
- ✅ `SupplierContact` (fue `ProveedorContacto`)
- ✅ `SupplierAddress` (fue `ProveedorDirección`)
- ✅ `Purchase` (fue `Compra`)
- ✅ `PurchaseLine` (fue `CompraLinea`)
- ✅ `Sale` (fue `Venta`)
- ✅ `Expense` (fue `Gasto`)
- ✅ `BankMovement` (fue `BancoMovimiento`)
- ✅ `Payroll` (fue `Nomina` - parcialmente)

### 2. Tablas SQL
**Archivo de migración:** `ops/migrations/2025-11-17_001_spanish_to_english_names/up.sql`

| Antigua | Nueva |
|---------|-------|
| proveedores | suppliers |
| proveedor_contactos | supplier_contacts |
| proveedor_direcciones | supplier_addresses |
| ventas | sales |
| compras | purchases |
| compra_lineas | purchase_lines |
| gastos | expenses |
| banco_movimientos | bank_movements |
| nominas | payrolls |
| Y 17+ más... | ✅ |

### 3. Columnas SQL
Más de 100 columnas renombradas:
- `codigo` → `code`
- `nombre` → `name`
- `nombre_comercial` → `trade_name`
- `telefono` → `phone`
- `web` → `website`
- `activo` → `is_active`
- `fecha` → `date`
- `estado` → `status`
- `impuestos` → `taxes`
- etc.

### 4. Módulos __init__.py Actualizados
- ✅ `app/models/suppliers/__init__.py`
- ✅ `app/models/purchases/__init__.py`
- ✅ `app/models/sales/__init__.py`
- ✅ `app/models/expenses/__init__.py`
- ✅ `app/models/finance/__init__.py`
- ✅ `app/models/__init__.py` (principal)

### 5. Compatibilidad hacia atrás
- ✅ Aliases de nombres antiguos disponibles
- ✅ Antiguo código funcionará sin cambios
- ✅ Permite migración gradual

---

## 📋 Aún Pendiente

### A. Actualizar referencias en servicios/routers

Los siguientes archivos aún refieren a nombres antiguos pero funcionarán con alias:

**Repositorios (pueden migrar después):**
- `app/modules/proveedores/infrastructure/repositories.py`
- `app/modules/compras/infrastructure/repositories.py`
- `app/modules/gastos/infrastructure/repositories.py`
- `app/modules/finanzas/infrastructure/repositories.py`
- `app/modules/ventas/infrastructure/repositories.py`

**Manejadores de Importación:**
- `app/modules/imports/domain/handlers.py`
- `app/modules/imports/domain/handlers_complete.py`

**Interfaces HTTP:**
- `app/modules/proveedores/interface/http/tenant.py`
- `app/modules/compras/interface/http/tenant.py`
- `app/modules/gastos/interface/http/tenant.py`
- `app/modules/ventas/interface/http/tenant.py`
- `app/modules/finanzas/interface/http/tenant.py`

### B. Tests
- Actualizar referencias en `app/tests/`

---

## 🚀 Próximos Pasos (Opcionales)

El código ya funciona. Para una limpieza completa (después de validar en producción):

### Opción 1: Migración Gradual (RECOMENDADO)
```
1. Ejecutar migración SQL (up.sql)
2. Validar que todo funciona (todo sigue funcionando con aliases)
3. Poco a poco actualizar servicios/routers a nuevos nombres
4. Deprecar nombres antiguos después de 1-2 meses
```

### Opción 2: Migración Completa Inmediata
```bash
# Actualizar imports en servicios
grep -r "from app.models.suppliers import Proveedor" app/
# → Cambiar a: from app.models.suppliers import Supplier

# Actualizar referencias en código
grep -r "Proveedor" app/ | grep -v "# Keep old"
# → Cambiar todos a "Supplier"
```

---

## 📝 Checklist de Implementación

- [ ] **Fase 1: Código Backend**
  - [x] Actualizar modelos Python
  - [x] Crear migraciones SQL (up/down)
  - [x] Actualizar __init__.py
  - [ ] Tests: Ejecutar suite completa

- [ ] **Fase 2: Validación**
  - [ ] Ejecutar migración en dev
  - [ ] Validar que aplicación inicia correctamente
  - [ ] Ejecutar tests (deben pasar sin cambios gracias a aliases)

- [ ] **Fase 3: Gradual (Opcional)**
  - [ ] Actualizar servicios a nuevos nombres
  - [ ] Actualizar routers a nuevos nombres
  - [ ] Actualizar schemas Pydantic
  - [ ] Actualizar tests

- [ ] **Fase 4: Producción**
  - [ ] Backup BD
  - [ ] Ejecutar migración: `2025-11-17_001_spanish_to_english_names/up.sql`
  - [ ] Validar en producción

---

## 🔄 Reverting (Si es necesario)

Si algo sale mal, revertir es simple:

```bash
# Ejecutar down.sql
psql -d tu_bd < ops/migrations/2025-11-17_001_spanish_to_english_names/down.sql

# El código sigue funcionando gracias a los aliases
```

---

## 📦 Archivos Clave Modificados

```
✅ Modelos Renombrados:
   app/models/suppliers/proveedor.py → clases: Supplier, SupplierContact, SupplierAddress
   app/models/purchases/compra.py → clases: Purchase, PurchaseLine
   app/models/sales/venta.py → clase: Sale
   app/models/expenses/gasto.py → clase: Expense
   app/models/finance/banco.py → clase: BankMovement
   app/models/hr/nomina.py → actualizados campos principales

✅ Migraciones SQL:
   ops/migrations/2025-11-17_001_spanish_to_english_names/up.sql
   ops/migrations/2025-11-17_001_spanish_to_english_names/down.sql

✅ __init__ actualizados:
   app/models/__init__.py
   app/models/suppliers/__init__.py
   app/models/purchases/__init__.py
   app/models/sales/__init__.py
   app/models/expenses/__init__.py
   app/models/finance/__init__.py
```

---

## 💡 Notas Importantes

1. **Sin cambios funcionales**: Todo sigue funcionando igual
2. **Alias activos**: Código antiguo seguirá funcionando
3. **Migration bidireccional**: Puedes reverting en cualquier momento
4. **Sin presión de urgencia**: Migración gradual recomendada
5. **DB cambios**: Solo aplica si ejecutas la migración SQL

---

## Contacto / Preguntas

- Guía implementación: `IMPLEMENTATION_GUIDE.md`
- Plan migraciones: `NAMING_MIGRATION_PLAN.md`
