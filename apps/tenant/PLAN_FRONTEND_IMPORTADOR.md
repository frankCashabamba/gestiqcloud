# Plan de Desarrollo - Frontend Importador

## Resumen Ejecutivo

El **frontend está 80% completo** con UI/UX profesional, pero necesita **integración con backend endpoints** para:
- ✅ Endpoints de clasificación IA
- ✅ Endpoints de plantillas CRUD
- ✅ WebSocket para progreso en tiempo real
- ✅ Validadores por país

---

## 1. Estado Actual

### ✅ Lo que SÍ está implementado

#### Componentes Core
- **Wizard.tsx** (6 pasos) - Flujo completo de importación
- **MapeoCampos.tsx** - Auto-mapeo con Levenshtein + Drag & Drop
- **ProgressIndicator.tsx** - Barra de progreso animada
- **TemplateManager.tsx** - Gestión de plantillas
- **PreviewPage.tsx** - Vista previa de lotes importados

#### Servicios
- **importsApi.ts** - Crear batches, subir archivos, ingestar datos
- **templates.ts** - CRUD plantillas (con fallback localStorage)
- **parseExcelFile.ts** - Parsear archivos Excel
- **columnMappingApi.ts** - Mapeo de columnas

#### Features
- ✅ Detección automática de tipo de documento
- ✅ Auto-mapeo con sugerencias de confianza
- ✅ Validación de filas (reglas de negocio)
- ✅ Normalización de documentos
- ✅ Drag & Drop de columnas
- ✅ Plantillas del sistema (Panadería, Bazar, Facturas)
- ✅ 6 pasos del wizard con breadcrumb
- ✅ Responsive design (mobile, tablet, desktop)

#### UX/UI
- ✅ Gradientes modernos
- ✅ Transiciones smooth
- ✅ Animaciones de carga
- ✅ Estados visuales (pending, processing, ready, saved, error)
- ✅ Badges de confianza coloreados
- ✅ Tooltips informativos

---

## 2. ❌ Lo que FALTA - Integraciones Backend

### 2.1 Endpoints de Clasificación IA (BLOQUEADOR)

**Status**: NO existe en backend  
**Prioridad**: ALTA  
**Dificultad**: MEDIA

#### Que necesita el frontend:

```typescript
// Paso 1: Clasificar archivo
POST /api/v1/imports/files/classify
{
  "file_path": "uploads/tmp/invoice_001.csv",
  "filename": "invoice_001.csv",
  "use_ai": true  // opcional, default true
}

Response:
{
  "suggested_parser": "csv_invoices",
  "confidence": 0.95,
  "doc_type": "invoice",
  "reason": "Detected invoice columns (invoice_number, total, vendor)",
  "probabilities": {
    "invoice": 0.95,
    "expense": 0.03,
    "bank_tx": 0.02
  },
  "enhanced_by_ai": true,
  "ai_provider": "local"
}
```

#### Componente que lo usa:

```typescript
// ImportadorExcel.tsx línea ~200
const classifyFile = async (file: File) => {
  // Actualmente NO hace nada, solo detecta por extensión
  // NECESITA: llamar a /imports/files/classify
  
  const result = await fetch('/api/v1/imports/files/classify', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData  // file + filename
  })
}
```

#### Backend que debe implementar:

```python
# app/modules/imports/interface/http/preview.py (EXISTE!)
# Línea ~273: classifier.classify_file() ya está implementado

# Pero falta exponerlo como endpoint:
@router.post('/imports/files/classify')
async def classify_file(
    file: UploadFile,
    use_ai: bool = Query(True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Clasificar archivo para determinar parser y doc_type."""
    tmp_path = save_temp_file(file)
    result = classifier.classify_file(str(tmp_path), file.filename)
    
    if use_ai and result['confidence'] < 0.7:
        ai_result = await classifier.classify_file_with_ai(
            str(tmp_path), file.filename
        )
        return ai_result
    
    return result
```

---

### 2.2 Endpoints de Plantillas (BLOQUEADOR)

**Status**: Partial (localStorage fallback)  
**Prioridad**: ALTA  
**Dificultad**: BAJA

#### Que necesita el frontend:

```typescript
// GET /api/v1/imports/templates
// Query params: source_type (opcional)
Response: ImportTemplate[]

// GET /api/v1/imports/templates/{id}
Response: ImportTemplate

// POST /api/v1/imports/templates
Body: {
  "name": "Mis Facturas",
  "source_type": "invoice",
  "mappings": { "invoice_date": "fecha", "amount": "total" }
}
Response: ImportTemplate

// DELETE /api/v1/imports/templates/{id}
Response: 204
```

#### Componentes que lo usan:

- **TemplateManager.tsx** - Listar + eliminar
- **MapeoCampos.tsx** - Cargar + guardar

#### Backend que debe implementar:

```python
# app/modules/imports/interface/http/templates.py (NUEVO)

@router.get('/imports/templates')
async def list_templates(
    source_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Listar plantillas del usuario + sistema."""
    
@router.post('/imports/templates')
async def create_template(
    template: ImportTemplateCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crear nueva plantilla."""

@router.get('/imports/templates/{template_id}')
async def get_template(template_id: str, ...):
    """Obtener plantilla por ID."""

@router.delete('/imports/templates/{template_id}')
async def delete_template(template_id: str, ...):
    """Eliminar plantilla del usuario."""
```

---

### 2.3 WebSocket de Progreso (IMPORTANTE)

**Status**: Simulado (fallback)  
**Prioridad**: MEDIA  
**Dificultad**: MEDIA

#### Que necesita el frontend:

```typescript
// useImportProgress.tsx
// WebSocket: /ws/imports/progress/{batch_id}

// Recibe cada 1s:
{
  "current": 150,
  "total": 500,
  "status": "processing",  // idle, processing, completed, error
  "message": "Validando fila 150 de 500...",
  "estimated_time_remaining": 45  // segundos
}
```

#### Componente que lo usa:

```typescript
// Paso 6 del Wizard
const { progress, error } = useImportProgress(batchId)
```

#### Backend que debe implementar:

```python
# app/modules/imports/interface/websocket.py (NUEVO)

@app.websocket("/ws/imports/progress/{batch_id}")
async def import_progress_ws(websocket: WebSocket, batch_id: str):
    await websocket.accept()
    
    while True:
        progress = await get_batch_progress(batch_id)
        await websocket.send_json(progress)
        
        if progress['status'] in ['completed', 'error']:
            break
        
        await asyncio.sleep(1)
```

---

### 2.4 Validadores por País (IMPORTANTE)

**Status**: Backend ✅ Existe (FASE C)  
**Prioridad**: MEDIA  
**Dificultad**: BAJA

#### Que necesita el frontend:

El Wizard paso 4 (ValidacionFilas) necesita:

```typescript
// Paso 4: Validación
const validationResult = await validateBatch(
  batchId,
  country: 'EC'  // o 'ES', 'MX', etc.
)

// Response:
{
  "valid": true/false,
  "errors": [
    "Row 5: Missing required field 'amount'",
    "Row 10: Invalid RUC format for EC"
  ]
}
```

#### Backend endpoint:

```python
# app/modules/imports/interface/http/preview.py (EXISTE PARCIALMENTE)
# Necesita mejorar:

@router.post('/imports/batches/{batch_id}/validate')
async def validate_batch(
    batch_id: str,
    country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Validar batch con reglas por país."""
    batch = db.query(ImportBatch).get(batch_id)
    
    errors = validate_canonical(batch.canonical_doc)
    
    if country:
        validator = get_validator_for_country(country)
        country_errors = validator.validate(batch.canonical_doc)
        errors.extend(country_errors)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
```

---

## 3. Plan de Implementación

### Fase 1: Endpoints de Clasificación (1-2 días)

**Objetivo**: Integrar IA con UI

**Tareas**:

1. ✅ Backend: Exponer `/api/v1/imports/files/classify`
   - Usar `classifier.classify_file_with_ai()` que ya existe
   - Soportar `use_ai` query param
   - Retornar estructura esperada

2. Frontend: Integrar en ImportadorExcel.tsx
   - Detectar cuando sube archivo
   - Llamar a classify endpoint
   - Mostrar `suggested_parser` y `confidence` al usuario
   - Permitir override manual

3. UX: Mostrar selector de tipo
   - Badge: "IA sugiere: Invoice (95%)"
   - Botón: "✓ Aceptar" o "✎ Cambiar"
   - Fallback a heurísticas si confidence < 0.7

**Estimado**: 1 día backend + 1 día frontend = **2 días**

---

### Fase 2: Endpoints de Plantillas (1-2 días)

**Objetivo**: Persistir plantillas en BD

**Tareas**:

1. Backend: CRUD endpoints
   - Crear tabla `import_templates`
   - GET /imports/templates
   - POST /imports/templates
   - GET /imports/templates/{id}
   - DELETE /imports/templates/{id}
   - Filtro por tenant_id + source_type

2. Frontend: Reemplazar localStorage
   - Actualizar services/templates.ts
   - Cambiar fetch calls
   - Eliminar localStorage fallback
   - Manejar errores de red (fallback local temporal)

3. DB: Migración
   - Crear tabla con índices
   - Plantillas del sistema (seed data)

**Estimado**: 1 día backend + 0.5 día frontend = **1.5 días**

---

### Fase 3: WebSocket de Progreso (1 día)

**Objetivo**: Actualización en tiempo real

**Tareas**:

1. Backend: WebSocket endpoint
   - Escuchar `/ws/imports/progress/{batch_id}`
   - Actualizar progreso desde task Celery
   - Enviar JSON cada 1s
   - Cerrar cuando complete/error

2. Frontend: Mejorar useImportProgress hook
   - Conectar a WebSocket real
   - Eliminar simulación
   - Manejar desconexiones
   - Reintentos automáticos

**Estimado**: 0.5 día backend + 0.5 día frontend = **1 día**

---

### Fase 4: Validadores por País (0.5 días)

**Objetivo**: Validación completa en UI

**Tareas**:

1. Backend: Mejorar endpoint `/imports/batches/{id}/validate`
   - Agregar soporte country param
   - Llamar a get_validator_for_country()
   - Retornar errors específicos

2. Frontend: Integrar en Paso 4
   - Selector de país (EC, ES, MX, etc.)
   - Mostrar errores específicos
   - Avisos contextuales

**Estimado**: 0.5 día backend + 0.5 día frontend = **1 día**

---

## 4. Arquitectura de Integración

### Flujo actual (Frontend-Backend)

```
Frontend                          Backend
=====================================

1. User upload file
   ├─→ POST /imports/batches       ✅ Funciona
   │   └─ returns batch_id
   │
   └─→ POST /imports/files/upload  ✅ Funciona
       └─ returns file_key

2. Auto-detect type
   ├─→ POST /imports/files/classify ❌ NO EXISTE
   │   └─ returns doc_type + parser
   │
   └─ Fallback: detect por extensión

3. Mapping
   ├─→ GET/POST /imports/templates  ⚠️ LocalStorage
   │   └─ returns plantillas
   │
   └─→ POST /imports/preview        ✅ Preview de datos

4. Validation
   ├─→ POST /imports/validate        ⚠️ Parcial
   │   └─ returns errors
   │
   └─ Fallback: validación local

5. Import
   ├─→ POST /imports/ingest          ✅ Funciona
   │   └─ returns job_id
   │
   └─→ WS /ws/imports/progress       ❌ Simulado
       └─ updates cada 1s
```

---

## 5. Prioridades

### 🔴 CRÍTICAS (Bloquean uso)
1. **Clasificación IA** - `/imports/files/classify` endpoint
2. **Plantillas DB** - `/imports/templates` endpoints

### 🟡 IMPORTANTES (Mejoran UX)
1. **WebSocket progreso** - tiempo real
2. **Validadores país** - validación completa

### 🟢 OPCIONALES (Futuros)
1. Dashboard de reportes
2. Histórico de importaciones
3. Estadísticas y métricas
4. Notificaciones por email

---

## 6. Archivos a Modificar

### Backend

| Archivo | Acción | Líneas | Esfuerzo |
|---------|--------|--------|----------|
| `app/modules/imports/interface/http/preview.py` | Agregar endpoint classify | +30 | 1h |
| `app/modules/imports/interface/http/templates.py` | Nuevo archivo CRUD | 150 | 3h |
| `app/modules/imports/interface/websocket.py` | Nuevo archivo WS | 80 | 2h |
| `app/modules/imports/models.py` | Agregar modelo ImportTemplate | 20 | 0.5h |
| `ops/migrations/` | Nueva migración tabla | 20 | 0.5h |

### Frontend

| Archivo | Acción | Líneas | Esfuerzo |
|---------|--------|--------|----------|
| `services/importsApi.ts` | Agregar classify call | +15 | 0.5h |
| `services/templates.ts` | Quitar localStorage, usar API | -30 +30 | 1h |
| `hooks/useImportProgress.tsx` | Conectar WebSocket real | -20 +20 | 1h |
| `ImportadorExcel.tsx` | Integrar classify en paso 1 | +30 | 1h |
| `components/ValidacionFilas.tsx` | Agregar selector país | +20 | 1h |

---

## 7. Estado de Componentes

### Componentes LISTOS (100%)

| Componente | Funcionalidad | Dependencia |
|------------|---------------|-------------|
| Wizard.tsx | 6 pasos flujo | Endpoints básicos ✅ |
| MapeoCampos.tsx | Auto-mapeo + Drag&Drop | Templates API ⚠️ |
| ProgressIndicator.tsx | Barra progreso animada | WebSocket ❌ |
| TemplateManager.tsx | Modal plantillas | Templates API ⚠️ |
| PreviewPage.tsx | Vista previa lotes | Endpoints básicos ✅ |
| ColumnMappingModal.tsx | Editor mapeo visual | Endpoint preview ✅ |
| ProcessingIndicator.tsx | Spinner de carga | - |
| VistaPreviaTabla.tsx | Tabla datos preview | - |
| PrintBarcodeLabels.tsx | Imprimir códigos QR | - |

### Servicios PARCIALES

| Servicio | Status | TODO |
|----------|--------|------|
| importsApi.ts | ✅ 90% | Agregar classify() |
| templates.ts | ⚠️ 50% | Reemplazar localStorage por API |
| parseExcelFile.ts | ✅ 100% | - |
| previewApi.ts | ✅ 100% | - |
| columnMappingApi.ts | ✅ 100% | - |

---

## 8. Testing Frontend

### Tests a agregar

```typescript
// tests/modules/importador/importsApi.test.ts
describe('classifyFile', () => {
  it('should call /imports/files/classify', async () => {
    const result = await classifyFile(file, true)
    expect(result.doc_type).toBe('invoice')
    expect(result.confidence).toBeGreaterThan(0)
  })
})

// tests/modules/importador/useImportProgress.test.ts
describe('useImportProgress', () => {
  it('should connect WebSocket', async () => {
    const { progress } = renderHook(() => useImportProgress(batchId))
    expect(progress.status).toBe('processing')
  })
})

// tests/modules/importador/TemplateManager.test.ts
describe('TemplateManager', () => {
  it('should load templates from API', async () => {
    const templates = await loadTemplates()
    expect(templates).toHaveLength(3)
  })
})
```

---

## 9. Variables de Entorno

```bash
# .env.local (frontend)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# .env (backend)
IMPORT_AI_PROVIDER=local  # o openai, azure
IMPORT_AI_CONFIDENCE_THRESHOLD=0.7
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_LOG_TELEMETRY=true
```

---

## 10. Roadmap

### Semana 1
- [ ] Implementar clasificación IA (backend + frontend) - 2 días
- [ ] Implementar CRUD plantillas (backend + frontend) - 1.5 días
- [ ] Testing básico - 1.5 días
- **Total**: ~5 días

### Semana 2
- [ ] WebSocket progreso - 1 día
- [ ] Validadores por país - 1 día
- [ ] Tests WebSocket + validación - 1 día
- [ ] Integración E2E - 1.5 días
- **Total**: ~4.5 días

### Semana 3
- [ ] Bug fixes y optimizaciones
- [ ] Documentación de usuario
- [ ] Deploy a staging

---

## 11. Checklist de Entrega

### Backend
- [ ] Endpoint `/api/v1/imports/files/classify`
- [ ] Endpoints CRUD `/api/v1/imports/templates`
- [ ] WebSocket `/ws/imports/progress/{batch_id}`
- [ ] Modelo `ImportTemplate` en BD
- [ ] Migración con tabla templates
- [ ] Tests unitarios
- [ ] Documentación API

### Frontend
- [ ] Integración classify en ImportadorExcel.tsx
- [ ] Eliminación localStorage en templates.ts
- [ ] Conexión WebSocket en useImportProgress.tsx
- [ ] Selector país en ValidacionFilas.tsx
- [ ] Tests integración
- [ ] Tests E2E con Playwright
- [ ] Documentación de usuario

### QA
- [ ] Flujo completo (upload → preview → mapeo → validación → import)
- [ ] Clasificación IA con baja/alta confianza
- [ ] Plantillas guardadas y cargadas
- [ ] Progreso en tiempo real
- [ ] Validación por país
- [ ] Responsive en móvil/tablet
- [ ] Manejo de errores de red

---

## 12. Conclusión

El frontend está **muy avanzado (80%)**, necesita solo:

1. **2 endpoints nuevos principales**:
   - `/imports/files/classify` (usa código existente)
   - `/imports/templates/*` (CRUD simple)

2. **1 WebSocket**:
   - `/ws/imports/progress/{batch_id}` (actualizar cada 1s)

3. **Mejorar 1 endpoint existente**:
   - `/imports/batches/{id}/validate` (agregar country param)

**Esfuerzo total**: ~10 días de desarrollo (4-5 backend + 4-5 frontend + testing)

**Bloqueadores**: Ninguno, todo es desarrollo nuevo pero bien definido.
