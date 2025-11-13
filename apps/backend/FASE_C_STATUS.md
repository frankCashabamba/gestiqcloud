# Fase C - Estado Actual y Tareas Pendientes

**Última revisión**: 11 Nov 2025  
**Completitud**: 65% 

---

## ✅ Completado en Fase C

### 1. Schema Canónico Extendido
- **Archivo**: `app/modules/imports/domain/canonical_schema.py`
- **Nuevos tipos**: `product` y `expense` (además de invoice, expense_receipt, bank_tx)
- **Funcionalidad**: 
  - Tipado TypedDict para ProductInfo y ExpenseInfo
  - Función `validate_canonical()` que valida estructura y restricciones
  - `build_routing_proposal()` para enrutamiento automático
  - **532 líneas de código**

### 2. Validadores Especializados
- **Archivo**: `app/modules/imports/validators/`
  - `products.py` - Validación individual y batch de productos
  - `expenses.py` - Validación individual y batch de gastos
  - `country_validators.py` - Validación por país (EC, ES, PE, CO, etc)
  - `error_catalog.py` - Códigos de error estandarizados

### 3. Handlers Funcionales
- **Archivo**: `app/modules/imports/domain/handlers.py`
- **4 Handlers Implementados**:
  - `InvoiceHandler` → inserta en tabla `invoices` + `invoice_lines`
  - `BankHandler` → inserta en tabla `bank_transactions`
  - `ExpenseHandler` → inserta en tabla `gastos`
  - `ProductHandler` → inserta en tabla `products` + gestión de stock
- **Características**:
  - Búsqueda/creación automática de entidades relacionadas
  - Soporte múltiples alias de campos
  - Idempotencia (no duplica si ya existe)
  - Transaccionalidad con try/catch
  - **870 líneas de código**

### 4. Router de Despacho
- **Archivo**: `app/modules/imports/domain/handlers_router.py`
- **Funcionalidad**:
  - Mapeo dinámico `doc_type` → Handler
  - Conversión canónico → formato normalizado
  - Método `promote_canonical()` para enviar a tabla destino

### 5. Tests Comprensivos
- **Archivo**: `tests/modules/imports/test_canonical_schema.py`
- **Cobertura**:
  - 8 tests ProductValidation (mínimo, completo, errores, validaciones)
  - 8 tests ExpenseValidation (igual cobertura)
  - 7 tests RoutingProposal
  - 6 tests TotalsValidation
  - Tests para parser registry y classifier
  - **547 líneas de código**

---

## 📋 Pendiente en Fase C

### 1. **Integración Celery** (Crítico)
**Estado**: NO INICIADO  
**Ubicación**: `app/modules/imports/application/tasks/task_import_file.py`

**Qué hacer**:
```python
# Actualizar task_import_file() para:
# 1. Pasar cada item por validate_canonical()
# 2. Usar HandlersRouter.promote_canonical() en lugar de handlers directos
# 3. Guardar canonical_doc en ImportItem
# 4. Guardar errores de validación

for item_data in parser_result['items']:
    # Validar contra schema canónico
    is_valid, errors = validate_canonical(item_data)
    
    if is_valid:
        # Despacho dinámico al handler correcto
        promote_result = HandlersRouter.promote_canonical(
            db, tenant_id, item_data
        )
    else:
        # Guardar errores
        import_item.validation_status = 'ERROR_SCHEMA'
        import_item.validation_errors = errors
```

### 2. **Validadores por País** (Ampliación)
**Estado**: Parcialmente implementado  
**Ubicación**: `app/modules/imports/validators/country_validators.py`

**Qué falta**:
- [ ] Validación RUC/NIF por país (EC, ES, PE, CO, MX)
- [ ] Validación de reglas fiscales por país
- [ ] Validación de IBAN según país
- [ ] Integración en `validate_canonical()` cuando country está presente

**Ejemplo**:
```python
# Agregar en validate_canonical() la línea 413-426:
if country:
    country_errors = validate_country_specific(data, country)
    errors.extend(country_errors)
```

### 3. **Persistencia de Documento Canónico** (BD)
**Estado**: NO INICIADO

**Cambios SQL necesarios**:
```sql
ALTER TABLE import_items ADD COLUMN IF NOT EXISTS (
    canonical_doc JSON,           -- Documento validado
    doc_type VARCHAR(50),          -- invoice|product|expense|etc
    validation_status VARCHAR(20)  -- OK|ERROR_SCHEMA|ERROR_BUSINESS
);

ALTER TABLE import_lineage ADD COLUMN IF NOT EXISTS (
    promotion_type VARCHAR(50)     -- tipo de documento promovido
);
```

**Qué hacer en código**:
- Actualizar modelo `ImportItem` (SQLAlchemy)
- Guardar `canonical_doc` después de validar
- Guardar `doc_type` detectado
- Guardar estado de validación

### 4. **Endpoints API para Validación** (Opcional)
**Qué agregar**:
- `GET /imports/batch/{id}/validation-status` - Estado de validación
- `GET /imports/item/{id}/canonical` - Ver documento canónico
- `GET /imports/item/{id}/validation-errors` - Errores de validación

---

## 📊 Cobertura Actual por doc_type

| doc_type | Schema | Validación | Handler | Router | Tests | Status |
|----------|--------|-----------|---------|--------|-------|--------|
| invoice | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| expense_receipt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| bank_tx | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| product | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| expense | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Validación por país** | - | 🔴 | - | - | - | ⏳ |
| **Celery integration** | - | - | - | - | - | ⏳ |
| **BD persistence** | - | - | - | - | - | ⏳ |

---

## 🚀 Recomendación: Siguiente Paso

### **Opción A - Crítico** (Recomendado)
Completar **Integración Celery** para que el flujo completo funcione:
1. Actualizar `task_import_file.py` 
2. Integrar `validate_canonical()` en el flow
3. Integrar `HandlersRouter.promote_canonical()`
4. Tests E2E

**Tiempo estimado**: 4-6 horas

### **Opción B - Seguridad**
Implementar **Validadores por País** para soporte fiscal:
1. Extender `country_validators.py`
2. Integrar en `validate_canonical()`
3. Tests por país

**Tiempo estimado**: 3-4 horas

### **Opción C - Rastreo**
Agregar **Persistencia de Documento Canónico**:
1. Migración SQL
2. Actualizar modelo ImportItem
3. Guardar en Celery task

**Tiempo estimado**: 2-3 horas

---

## 📚 Archivos Clave

```
app/modules/imports/
├── domain/
│   ├── canonical_schema.py          (✅ COMPLETO - 532 líneas)
│   ├── handlers.py                  (✅ COMPLETO - 870 líneas)
│   └── handlers_router.py           (✅ COMPLETO - 175 líneas)
├── validators/
│   ├── products.py                  (✅ EXISTENTE)
│   ├── expenses.py                  (✅ EXISTENTE)
│   └── country_validators.py        (⏳ A EXTENDER)
├── application/
│   └── tasks/
│       └── task_import_file.py      (⏳ A INTEGRAR)
└── DOCUMENTACIÓN/
    ├── FASE_C_SUMMARY.md            (✅ ESTE DOCUMENTO)
    └── FASE_C_IMPLEMENTACION.md     (✅ DETALLE TÉCNICO)

tests/modules/imports/
└── test_canonical_schema.py         (✅ 16+ TESTS)
```

---

## ✨ Checklist de Implementación Fase C

### Core (HECHO)
- [x] Extender canonical_schema.py con product + expense
- [x] Crear ProductInfo y ExpenseInfo TypedDict
- [x] Función validate_canonical() robusta
- [x] Handlers para invoice, bank, expense, product
- [x] Router de despacho dinámico
- [x] 16+ tests con buena cobertura

### Integración (PENDIENTE)
- [ ] Integrar validate_canonical() en Celery task
- [ ] Usar HandlersRouter.promote_canonical() en lugar de handlers directos
- [ ] Guardar canonical_doc en BD
- [ ] Extender validadores por país

### Próximo Paso: Fase D
- [ ] IA configurable (local/pago)
- [ ] Endpoint `/imports/files/classify`
- [ ] Mejora de confianza con feedback

---

**Creado por**: Revisión Fase C  
**Próxima actualización**: Después de completar Integración Celery
