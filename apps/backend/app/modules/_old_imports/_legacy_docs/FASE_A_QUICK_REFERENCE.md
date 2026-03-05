# 🟢 Fase A - Quick Reference (71% Operativa)

## 📍 Ubicación de Archivos Clave

| Componente | Archivo | Líneas | Estado |
|-----------|---------|--------|--------|
| Modelo ORM | `models/core/modelsimport.py` | 50-53, 72-73 | ✅ |
| Schemas | `schemas.py` | 65-100 | ✅ |
| Endpoints | `interface/http/tenant.py` | 731, 748, 803 | ✅ |
| Classifier | `services/classifier.py` | N/A | ✅ |

---

## 🔌 Endpoints Operativos

### 1. Crear Batch con Clasificación
```bash
POST /api/v1/imports/batches
Content-Type: application/json

{
  "source_type": "invoices",
  "origin": "excel",
  "file_key": "uploads/tenant123/file.xlsx",
  "suggested_parser": "excel_invoices",
  "classification_confidence": 0.95,
  "ai_enhanced": true,
  "ai_provider": "openai"
}
```

**Respuesta**: `BatchOut` con todos los campos

---

### 2. Actualizar Clasificación Manualmente
```bash
PATCH /api/v1/imports/batches/{batch_id}/classification
Content-Type: application/json

{
  "suggested_parser": "updated_parser",
  "classification_confidence": 0.85,
  "ai_enhanced": false,
  "ai_provider": "azure"
}
```

**Función**: `update_classification()` (línea 748)

---

### 3. Clasificar Archivo y Persistir
```bash
POST /api/v1/imports/batches/{batch_id}/classify-and-persist
Content-Type: multipart/form-data

file: <archivo.xlsx>
```

**Respuesta**: `BatchOut` actualizado con resultado de clasificación

**Flujo**:
1. Recibe archivo
2. Llama a `classifier.classify_file_with_ai()`
3. Persiste en `ImportBatch`:
   - `suggested_parser`
   - `classification_confidence`
   - `ai_enhanced`
   - `ai_provider`
4. Retorna batch actualizado

**Función**: `classify_and_persist_to_batch()` (línea 803)

---

## 📊 Campos de Fase A en ImportBatch

```python
suggested_parser: String | None      # Parser recomendado
classification_confidence: Float | None  # Score 0.0-1.0
ai_enhanced: Boolean                 # ¿Mejorado por IA?
ai_provider: String | None           # 'local'|'openai'|'azure'
```

**Índices**:
- `ix_import_batches_ai_provider`
- `ix_import_batches_ai_enhanced`

---

## 🔐 Seguridad

- ✅ RLS (Row-Level Security) en todos los endpoints
- ✅ Validación de `tenant_id`
- ✅ Prevención de acceso cross-tenant

---

## 📝 Ejemplo Completo

```python
# 1. Crear batch
batch = POST /imports/batches {
    "source_type": "invoices",
    "origin": "excel",
    "file_key": "uploads/..."
}
# → batch.id = uuid

# 2. Clasificar y persistir
result = POST /imports/batches/{batch.id}/classify-and-persist
    files: { file: "archivo.xlsx" }
# → result contiene suggested_parser, confidence, etc.

# 3. Override manual si es necesario
updated = PATCH /imports/batches/{batch.id}/classification
    json: { "suggested_parser": "new_parser" }
# → updated refleja cambio
```

---

## 🧪 Tests Pendientes

Crear en: `tests/modules/imports/test_phase_a_classification.py`

```python
class TestPhaseAClassification:
    def test_create_batch_with_classification(self, db, test_tenant_id)
    def test_patch_classification_endpoint(self, client, test_tenant_id)
    def test_classify_and_persist(self, client, test_tenant_id)
    def test_rls_isolation(self, client, tenant1_id, tenant2_id)
```

---

## 🚀 Próximos Pasos

1. ✅ Verificar endpoints en staging
2. ⚠️ Crear migración Alembic (si BD requiere)
3. ❌ Escribir tests de integración
4. 📚 Documentar en OpenAPI/Swagger

---

**Última actualización**: Nov 11, 2025
**Estado**: OPERATIVO (71%)
**Bloqueadores**: 0
