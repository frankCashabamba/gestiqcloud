# Módulo Importador de GestiqCloud - Documento Técnico Completo

## 1. Resumen general

El módulo importador es un sistema universal de importación y procesamiento de documentos contables que automatiza la extracción de datos, clasificación de tipos de documento y aprendizaje iterativo para mejorar la precisión en futuras importaciones.

### Flujo de alto nivel de una importación

```
1. RECEPCIÓN
   ├─ Upload de archivos (batch async)
   ├─ Validación de tipo y tamaño
   └─ Deduplicación por hash SHA256

2. OCR / EXTRACCIÓN DE TEXTO
   ├─ PDF → render a imágenes (300 DPI)
   ├─ Imágenes → Tesseract + EasyOCR
   ├─ Excel → lectura estructurada
   ├─ Caching de resultados OCR
   └─ Estimación de calidad de texto

3. PRE-CLASIFICACIÓN (5 CAPAS)
   ├─ L1: Snapshot cache (recetas aprend.) → skip AI
   ├─ L2: Filename pattern matching
   ├─ L3: Header mapping (campos canónicos)
   ├─ L4: Vendor/RUC + snapshot
   └─ L5: Template extraction (regex/labels) → skip AI si confianza >= threshold

4. LLAMADA A IA (si pre-clasificación no skipea)
   ├─ Prompting dinámico con contexto temporal
   ├─ Extracción de campos canónicos
   ├─ Detección de tablas/líneas
   └─ Enriquecimiento con OCR repairs

5. EXTRACCIÓN DE CAMPOS
   ├─ Normalización de datos extraídos
   ├─ Mapeo de columnas a campos canónicos
   ├─ Canonicalización de valores
   └─ Detección de tipos (factura, nota, recibo, etc.)

6. ROUTING / DECISIÓN DE REVISIÓN
   ├─ Matching de reglas de routing
   ├─ Validación de campos requeridos
   ├─ Cálculo de confianza
   └─ Determinación si requiere revisión humana

7. GUARDADO EN BD
   ├─ Documento en estado REVIEW o CONFIRMED
   ├─ Líneas de staging (para tablas)
   └─ Logs de auditoría

8. STAGING LINES (para líneas de tabla)
   ├─ Una fila por línea extraída
   ├─ Estado: PENDING, VALID, IMPORTED, INVALID, REVIEW, SKIPPED, REPROCESS
   └─ Soporte para re-procesamiento iterativo
```

### Tipos de archivos soportados

- **Imágenes**: PDF, PNG, JPG, JPEG, HEIC, HEIF, TIFF, BMP, GIF
- **Estructurados**: XLSX, XLS, CSV, XML, TXT, ZIP
- Extensiones configurables en `runtime_config.py`

---

## 2. Base de datos

### Tablas principales (prefijo `imp_` e `icu_`)

#### `imp_documento` — Documento subido y procesado
**Propósito**: Núcleo del sistema. Cada archivo importado genera un registro.

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id` (FK tenants)
- `nombre_archivo`, `tipo_archivo`, `tamanio_bytes`, `hash_sha256`
- `tipo_documento_detectado`, `confianza_clasificacion`, `requiere_revision` — AI results
- `texto_ocr`, `datos_extraidos`, `datos_confirmados` — Extracted and confirmed fields
- `estado` (PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED)
- `proveedor_detectado`, `ruc_detectado`, `monto_total`, `moneda`, `fecha_documento`
- `recipe_snapshot_id` (FK icu_recipe_snapshot) — Learning snapshot used
- `saved_as`, `saved_record_id`, `saved_at` — Created record reference (expense, purchase, etc.)
- `synced_recipe_id` — Recipe created from this document
- `llm_model`, `raw_ai_json` — AI traceability
- `fingerprint_json`, `sheet_profiles_json` — Structural metadata

**Índices**: tenant_id, estado, hash_sha256, created_at

**Relaciones**:
- 1:N `ImpLogCambios` (logs)
- 1:N `ImpRoutingSignal` (routing events)
- 1:N `ImpBatchItem` (batch tracking)
- 1:N `ImpStagingLine` (extracted lines)
- 1:N `ImpIteration` (reprocessing iterations)

**Estado**: Activamente usado en producción

---

#### `imp_batch_import` — Lote de importación async
**Propósito**: Agrupa múltiples archivos subidos en una sesión.

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id`, `usuario_id`
- `estado` (PENDING, PROCESSING, PARTIAL, COMPLETED, FAILED)
- `total_items`, `force_reprocess`
- `recipe_snapshot_id` (FK) — Optional snapshot to apply
- `completed_at`, `created_at`, `updated_at`

**Índices**: tenant_id, estado, created_at

**Relaciones**: 1:N `ImpBatchItem`

**Estado**: Activamente usado (creado 2026-03-09)

---

#### `imp_batch_item` — Archivo dentro del lote
**Propósito**: Tracking de cada archivo en el batch.

**Columnas clave**:
- `id` (UUID PK)
- `batch_id` (FK), `tenant_id` (FK), `documento_id` (FK, nullable)
- `nombre_archivo`, `tamanio_bytes`, `hash_sha256`, `orden`
- `estado` (PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED, REJECTED)
- `error_detalle`

**Índices**: batch_id, documento_id, tenant_id

**Relaciones**: Many:1 `ImpBatchImport`, Many:1 `ImpDocumento`

**Estado**: Activamente usado

---

#### `imp_log_cambios` — Auditoría de acciones
**Propósito**: Historial completo de cada documento.

**Columnas clave**:
- `id` (UUID PK)
- `documento_id` (FK)
- `accion` (UPLOAD, CLASSIFY, EXTRACT, VALIDATE, CONFIRM, EDIT, REJECT)
- `detalle` (JSON metadata)
- `usuario_id`
- `created_at`

**Índices**: documento_id, created_at

**Relaciones**: Many:1 `ImpDocumento`

**Estado**: Activamente usado

---

#### `imp_staging_line` — Líneas extraídas de tablas
**Propósito**: Desglose de filas para documentos estructurados (facturas con líneas).

**Columnas clave**:
- `id` (UUID PK)
- `documento_id` (FK)
- `tenant_id` (FK)
- `line_number`, `sheet_name`
- `raw_data`, `normalized_data` (JSON)
- `estado` (PENDING, VALID, IMPORTED, INVALID, REVIEW, SKIPPED, REPROCESS)
- `error_code`, `error_detail`
- `campos_revision` (JSON list of fields to review)
- `target_table`, `target_id`, `imported_at`

**Índices**: documento_id, tenant_id, estado, created_at

**Relaciones**: Many:1 `ImpDocumento`, 1:N `ImpLineErrorLog`

**Estado**: Activamente usado (para reprocesamiento iterativo)

---

#### `imp_iteration` — Reprocesamiento iterativo
**Propósito**: Tracking de intentos de re-procesamiento de filas.

**Columnas clave**:
- `id` (UUID PK)
- `documento_id` (FK), `tenant_id` (FK)
- `iteration_num`, `scope` (ALL, SELECTIVE)
- `scope_filter` (JSON criteria)
- `lines_attempted`, `lines_imported`, `lines_errored`, `lines_skipped`
- `improvement` (boolean, null mientras corre)
- `estado` (RUNNING, DONE, PARTIAL, NO_IMPROVEMENT, ABORTED)
- `llm_model`, `snapshot_id` (FK)
- `started_at`, `completed_at`, `initiated_by`

**Índices**: documento_id, tenant_id, created_at

**Relaciones**: Many:1 `ImpDocumento`, 1:N `ImpLineErrorLog`

**Estado**: Activamente usado

---

#### `imp_routing_profile` — Perfil de routing
**Propósito**: Define dónde debe enviarse cada tipo de documento (expense, recipe, supplier_invoice).

**Columnas clave**:
- `id` (UUID PK)
- `code`, `document_type`
- `description`, `suggested_destination`
- `required_groups` (JSON list of OR-groups of required fields)
- `support_fields`, `explanation_fields`
- `blocked`, `confidence_threshold`, `active`

**Índices**: code (unique)

**Relaciones**: 1:N `ImpRoutingRule`

**Estado**: Activamente usado (sistema de toma de decisiones)

---

#### `imp_routing_rule` — Regla de routing
**Propósito**: Mapea doc_type o categoría a un profile, por tenant y sector.

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id` (FK, nullable), `sector` (nullable)
- `source_kind` (doc_type | category)
- `source_key` (el valor a matchear)
- `profile_code` (FK imp_routing_profile)
- `priority`, `active`

**Índices**: tenant_id, sector, source_key, profile_code

**Relaciones**: Many:1 `ImpRoutingProfile`

**Estado**: Activamente usado (lookup en routing decisions)

---

#### `imp_routing_signal` — Eventos de routing para aprendizaje
**Propósito**: Registra cada decisión humana (save, edit, reject) para retroalimentación.

**Columnas clave**:
- `id` (UUID PK)
- `documento_id` (FK), `tenant_id` (FK)
- `event` (confirm | edit | save | reject)
- `user_id`, `chosen_destination`
- `changed_fields` (JSON list)
- `routing_snapshot` (JSON de DocumentRoutingDecision en el momento)
- `payload` (JSON metadata adicional)

**Índices**: documento_id, tenant_id, created_at

**Relaciones**: Many:1 `ImpDocumento`

**Estado**: Activamente usado (feedback loop learning)

---

#### `icu_recipe` — Receta de importación
**Propósito**: Contenedor de receta (colección de drafts + snapshots).

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id` (FK)
- `name`, `description`
- `is_public`, `created_by`, `archived`

**Relaciones**: 1:N `IcuRecipeDraft`, 1:N `IcuRecipeSnapshot`

**Estado**: Activamente usado

---

#### `icu_recipe_draft` — Borrador editable de receta
**Propósito**: Versión en edición de una receta.

**Columnas clave**:
- `id` (UUID PK)
- `recipe_id` (FK), `tenant_id` (FK)
- `prompt_system`, `prompt_user`
- `model_config` (JSON)
- `updated_by`, `created_at`, `updated_at`

**Relaciones**: Many:1 `IcuRecipe`

**Estado**: Activamente usado

---

#### `icu_recipe_snapshot` — Versión congelada de receta
**Propósito**: Snapshot inmutable de una receta en un momento específico.

**Columnas clave**:
- `id` (UUID PK)
- `recipe_id` (FK), `draft_id` (FK)
- `tenant_id` (FK)
- `version_tag`
- `content_json` (prompts + model config congelados)
- `created_by`, `created_at`

**Índices**: recipe_id, tenant_id, created_at

**Relaciones**: Many:1 `IcuRecipe`

**Estado**: Activamente usado (linked from imp_documento.recipe_snapshot_id)

---

#### `imp_config` — Configuración runtime
**Propósito**: Parámetros ajustables sin redeploy.

**Columnas clave**:
- `id` (UUID PK)
- `module` (sub-módulo: pre_classifier, ocr, classification, learning, etc.)
- `key`, `value_text`, `value_list`
- `label` (documentación)
- `updated_at`

**Índices**: module, key

**Estado**: Activamente usado (reemplaza sector_field_defaults)

---

#### `imp_vendor_snapshot` — Mapeo proveedor ↔ snapshot
**Propósito**: Capa L4 del pre-clasificador: acelera clasificación si se reconoce RUC del proveedor.

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id` (FK)
- `ruc`, `vendor_norm`
- `recipe_snapshot_id` (FK)
- `confirmed_count`, `last_seen_at`, `active`

**Índices**: tenant_id, ruc, created_at

**Estado**: Activamente usado

---

#### `imp_doc_type_template` — Plantilla de extracción (Capa L5)
**Propósito**: Reglas regex/label_search para saltar IA.

**Columnas clave**:
- `id` (UUID PK)
- `tenant_id` (FK, nullable)
- `doc_type`, `nombre`
- `activo`, `prioridad`
- `activacion_json` (condiciones: filename_patterns, text_keywords, min_text_length, tipo_archivo)
- `extraccion_json` (fields: regex, label_search, tipo)
- `min_confidence_para_skip`, `campos_requeridos`
- `total_usos`, `total_exitosos`, `last_used_at`

**Índices**: tenant_id, doc_type, activo

**Estado**: Activamente usado

---

#### Tablas de learning (implícitas en runtime_config.py)

- `imp_filename_pattern` — Patrones de filename aprendidos
- `imp_header_doc_type` — Canonical field sets → doc_type
- `imp_field_alias` — Column name → canonical field mappings
- `imp_column_candidate` — Unknown columns pending assignment

**Estado**: Parcialmente documentadas; almacenadas en imp_config o en tablas legacy

---

### Diagrama de relaciones (simplificado)

```
tenants (1)
  ├─ ImpDocumento (N) ←─ ImpLogCambios (N)
  │                   ├─ ImpBatchItem (N)
  │                   ├─ ImpRoutingSignal (N)
  │                   ├─ ImpStagingLine (N) ←─ ImpLineErrorLog (N)
  │                   ├─ ImpIteration (N)
  │                   └─ FK icu_recipe_snapshot
  ├─ ImpBatchImport (N) ─ ImpBatchItem (N) → ImpDocumento
  ├─ ImpRoutingProfile (N) ← ImpRoutingRule (N)
  ├─ IcuRecipe (N)
  │   ├─ IcuRecipeDraft (N)
  │   └─ IcuRecipeSnapshot (N) ← ImpDocumento & ImpVendorSnapshot
  ├─ ImpVendorSnapshot (N) → icu_recipe_snapshot
  ├─ ImpDocTypeTemplate (N) [tenant_id nullable]
  └─ ImpConfig (N) [configuración]
```

---

## 3. Backend — Arquitectura de archivos

### Archivo: `router.py`
**Responsabilidad**: Endpoints HTTP principales del módulo (upload, list, detail, confirm, edit, reprocess).

**Funciones/clases clave**:
- Rutas FastAPI: POST /documents, GET /documents/{id}, PATCH /documents/{id}/confirm, etc.
- Gestión de subidas asincrónicas
- Serialización de responses (DocumentoOut, BatchSummaryOut, etc.)

**Interactúa con**: batch_service, crud, processing_service, tasks

---

### Archivo: `batch_service.py`
**Responsabilidad**: Coordinación de lotes de importación asincrónica.

**Funciones/clases clave**:
- `enqueue_async_batch()` — Recibe lista de archivos, valida, deduplica, los pone en cola
- Deduplicación: hash exacto + nombre archivo + tamaño
- Reprocess detection: Si es mismo hash + estado CONFIRMED, puede re-procesar con learning
- `_ensure_batch_tracking_storage()` — Auto-crea tablas si faltan
- `_build_reprocess_context()` — Contexto para re-procesamiento (modo fast/deep)

**Interactúa con**: crud, ocr_service, auto_recipe, snapshot_learning, tasks, batch_tracking

**Estado de archivo**: Core. Contiene lógica crítica de deduplicación y reprocess.

---

### Archivo: `processing_service.py`
**Responsabilidad**: Orquestación del flujo completo de procesamiento de un documento.

**Funciones/clases clave**:
- `_process_document()` — Main pipeline
- Etapas: OCR → Pre-clasificación → AI (si needed) → Extracción → Routing → Guardado
- Timing/tracking de cada etapa
- Manejo de reprocess (fast vs deep)

**Interactúa con**: ocr_service, pre_classifier, ai_classifier, doc_type_resolution, document_routing_agent, iteration_service, crud, analysis_normalizer

**Estado**: Core del procesamiento

---

### Archivo: `pre_classifier.py`
**Responsabilidad**: Clasificación sin IA en 5 capas.

**Funciones/clases clave**:
- `classify_before_ai()` — Main entry point, retorna PreClassResult o None
- `PreClassResult` dataclass: doc_type, confidence, layer, reasoning, skip_ai, cached_analysis
- Capas:
  1. `L1_snapshot_cache` — cached_analysis from recipe_snapshot
  2. `L2_filename_pattern` — regex patterns en imp_filename_pattern
  3. `L3_header_mapping` — canonical field sets
  4. `L4_vendor_ruc` — RUC recognition + vendor snapshots
  5. `L5_template_match` — regex/label_search extraction

**Interactúa con**: field_alias_loader, ocr_service (indirectly via pre_class), runtime_config, database queries

**Caching**: 5 minutos (configurable)

---

### Archivo: `ai_classifier.py`
**Responsabilidad**: Llamada a LLM (Claude, Ollama, etc.) para extracción de campos.

**Funciones/clases clave**:
- `analyze_document()` — Llamada a AIService
- Prompt dinámico: contexto temporal, instrucciones por doc_type
- `_apply_high_evidence_ocr_repairs()` — Fixes basados en OCR de alta confianza
- `_estimate_text_quality()` — Calidad del OCR (weird ratio, suspicious chars)
- `_resolve_model_for_doctype()` — Routing de modelos por tipo doc

**Interactúa con**: AIService, runtime_config, ocr_service, document_fields

**Estado**: Crítico (costoso en tokens)

---

### Archivo: `ocr_service.py`
**Responsabilidad**: Extracción de texto de PDFs, imágenes y archivos estructurados.

**Funciones/clases clave**:
- `extract_text_from_file()` — Dispatcher por tipo
- PDF: PIL render a imágenes (300 DPI) → Tesseract/EasyOCR
- Imágenes: EasyOCR con múltiples PSM modes + rotations
- Excel: openpyxl, preserva estructura, detecta tablas
- CSV/XML/TXT: parseo directo
- Caching: hash SHA256 del archivo
- `detect_file_type()` — Por extensión

**Interactúa con**: Tesseract, EasyOCR, openpyxl, PIL, runtime_config

**Estado**: Performance-critical; caching activo

---

### Archivo: `classifier_learning.py`
**Responsabilidad**: Aprendizaje automático de patrones pre-clasificador.

**Funciones/clases clave**:
- `learn_from_confirmation()` — Main entry point (llamado después de confirmar documento)
- Aprende:
  - Patrones filename (imp_filename_pattern)
  - Header→doc_type mappings (imp_header_doc_type)
  - Field aliases globales (imp_field_alias)
- `_learn_filename()` — Incrementa confirmed/failed counts, promociona nuevos patrones
- `_learn_header_mapping()` — Hash de canonical fields → doc_type
- `_learn_column_aliases()` — Nombres de columna desconocidos
- `learn_column_candidates()` — Guarda en imp_column_candidate para revisión
- `learn_vendor_snapshot()` — Asocia RUC con snapshot

**Interactúa con**: database (upserts), field_alias_loader, canonical_document

**Estado**: Self-feeding loop, no requiere intervención humana

---

### Archivo: `crud.py`
**Responsabilidad**: CRUD operations para documentos y batches.

**Funciones/clases clave**:
- `create_documento()`, `get_documento()`, `update_documento()`
- `find_existing_documento()` — Dedupe logic (hash priority)
- `find_latest_documento_by_name()` — Versioning support
- `link_documento_successor()` — Relationship tracking (predecessor→successor)
- `list_documento_versions()` — BFS para recorrer cadena de versiones
- `reset_documento_for_reprocess()` — Limpia estado para reprocesamiento
- `create_batch()`, `summarize_batch()`, `refresh_batch_status()`
- `mark_document_staging_imported()` — Marca lines como IMPORTED
- `add_log()` — Auditoría

**Interactúa con**: ImpDocumento, ImpBatchImport, ImpLogCambios, database

**Estado**: Utility layer, usado ampliamente

---

### Archivo: `schemas.py`
**Responsabilidad**: Pydantic models para input/output API.

**Clases clave**:
- `DocumentoOut`, `DocumentoDetailOut` — Response
- `DocumentRoutingDecision` — Decisión de routing
- `BatchSummaryOut`, `BatchDetailOut`, `BatchItemOut`
- `StagingLineOut`, `StagingLineSummary`
- `IterationOut`, `IterationResultOut`, `RunIterationRequest`
- `SaveDocumentRequest` → `SaveDocumentResponse`
- `RoutingProfileAdminIn/Out`, `RoutingRuleAdminIn/Out`
- `RoutingPreviewRequest` → `RoutingPreviewResponse`

**Estado**: Type definitions, no lógica

---

### Archivo: `constants.py`
**Responsabilidad**: Constantes compartidas.

**Contenido**:
- `INTERNAL_STRUCTURAL_KEYS` (frozenset) — Claves metadata del sistema (filas, columnas, hojas, etc.) que se excluyen del aprendizaje

**Estado**: Minimalisista

---

### Archivo: `runtime_config.py`
**Responsabilidad**: Carga de configuración desde BD (imp_config) con fallbacks.

**Funciones clave**:
- `load_pre_classifier_runtime_config()`
- `load_ocr_runtime_config()`
- `load_learning_config()`
- `load_classification_threshold()`
- `load_ai_runtime_config()`
- `load_file_support_config()`
- `load_prompt_config()`
- Y muchas más (40+ config loaders)
- Caching con TTL configurable (default 300s)

**Estado**: Clave para configuración sin redeploy

---

### Archivo: `document_routing_agent.py` (en services/)
**Responsabilidad**: Toma de decisión: ¿dónde enviar el documento? (expense, recipe, supplier_invoice)

**Funciones clave**:
- `build_document_routing_decision()` — Main logic
- Evalúa reglas (ImpRoutingRule) por tenant, sector, doc_type, categoría
- Valida campos requeridos (required_groups)
- Calcula confidence final
- Retorna DocumentRoutingDecision con destination, missing_fields, needs_human_review

**Interactúa con**: document_routing_config, imp_routing_rule, imp_routing_profile

---

### Archivo: `iteration_service.py` (en services/)
**Responsabilidad**: Reprocesamiento iterativo de líneas de staging.

**Funciones clave**:
- `upsert_staging_lines_from_extraction()` — Crea/actualiza staging lines desde extraction result
- `fetch_lines_for_scope()` — Filtra líneas por scope (ALL, SELECTIVE con filtros)
- `run_iteration_on_scope()` — Re-procesa líneas seleccionadas
- `create_iteration()`, `close_iteration()` — Lifecycle
- `update_staging_line_estado()` — Transiciones de estado

**Interactúa con**: ImpStagingLine, ImpIteration, processing_service

---

### Archivo: `field_alias_loader.py`
**Responsabilidad**: Carga mapeos canonical_field ← alias (nombres de columna).

**Funciones clave**:
- `get_field_aliases()` — Retorna dict[canonical_field → list[alias]]
- `get_canonical_fields()` — Metadatos de campos canónicos (type, projection, slots)
- Caching con fallbacks

---

### Archivo: `canonical_document.py`
**Responsabilidad**: Construcción del documento canónico (vista normalizada).

**Funciones clave**:
- `build_document_projection()` — Mapea extracted fields a canonical schema
- Usa field aliases para resolver columnas
- Retorna dict con valores normalizados

---

### Archivo: `auto_recipe.py`
**Responsabilidad**: Detección automática de recetas aplicables y caching.

**Funciones clave**:
- `resolve_auto_recipe()` — Busca snapshot por fingerprint/headers
- `should_reprocess_existing_document()` — Decide si reruns por learning updates
- `get_snapshot_learning()` — Extrae learning info del snapshot
- `remember_snapshot_learning()` — Guarda aprendizaje para usar en futuras docs

---

### Archivo: `text_fallback_extractor.py`
**Responsabilidad**: Extracción de campos y líneas desde OCR puro (fallback si IA falla).

**Funciones clave**:
- `extract_fields_from_text()` — Label search + regex fallback
- `extract_line_items_table_preview_from_text()` — Tablas desde OCR

---

### Archivo: `analysis_normalizer.py`
**Responsabilidad**: Normalización del output AI (limpieza, validación, tipos).

---

### Archivo: `api_lifecycle.py`
**Responsabilidad**: Hooks de ciclo de vida API (confirmation, editing, saving).

---

### Archivo: `product_import_service.py`
**Responsabilidad**: Lógica de sincronización de productos desde documentos.

---

### Archivo: `daily_log_service.py`
**Responsabilidad**: Procesamiento de daily logs / registros de caja.

---

### Archivo: `tasks.py`
**Responsabilidad**: Tareas async (Celery). Entry point para procesamiento en background.

**Funciones clave**:
- `process_document_task.delay()` — Enqueue document processing
- `_run_processing()` — Async task handler

---

### Archivo: `recipe_crud.py`, `recipe_router.py`, `recipes_router.py`
**Responsabilidad**: CRUD y endpoints de recetas.

---

## 4. Backend — Flujo detallado de procesamiento

### Paso 1: Recepción (router.py + batch_service.py)

```python
# POST /documents/upload
enqueue_async_batch(
    files=[...],
    tenant_id=UUID,
    user_id=str,
    force=False,  # Ignore dedup
    recipe_snapshot_id=None,  # Optional pre-selected recipe
    reprocess_mode="fast"  # Or "deep"
)
```

**Validaciones**:
1. ¿Archivo vacío? → Skip
2. ¿Nombre temp (temático ~ $, .DS_Store)? → Skip
3. ¿Tamaño > límite individual? → Error 413 (Excel sin límite)
4. ¿Batch total > límite? → Error 413
5. ¿Archivo duplicado? → Reutilizar si CONFIRMED/REVIEW (sin force), o reenqueue si PENDING/PROCESSING
6. ¿Mismo hash + CONFIRMED + learning updates pendientes? → Reprocess (learning_update)
7. ¿Mismo hash + no force? → Skip (documento ya existe)

**Resultado**:
- Crea `ImpBatchImport` en estado PENDING
- Crea `ImpBatchItem` por archivo (orden preservado)
- Para nuevos: crea `ImpDocumento` con estado PENDING
- Para reus/rerun: reutiliza o resetea documento
- Enqueue Celery task `process_document_task` para cada documento

---

### Paso 2: Validación previa (ocr_service.py)

```python
# En _run_processing()
tipo_archivo = detect_file_type(filename)
# Valida extensión

# Carga archivo en memoria
file_bytes = load_payload(doc_id)
```

---

### Paso 3: OCR / Extracción de texto (ocr_service.py)

**Para PDFs**:
1. Convierte a imágenes (PIL + pdf2image, 300 DPI)
2. Aplica enhancements: contrast, sharpness
3. Tesseract + EasyOCR en paralelo
4. Elige mejor resultado por calidad
5. Preserva page numbers y bounding boxes

**Para Imágenes**:
1. EasyOCR con 3 PSM modes primarios
2. Rotaciones menores (-4, -2, 2, 4 grados)
3. Enhancement: autocontrast, threshold, perspective

**Para Excel**:
1. openpyxl.load_workbook(read_only=True) → memoria low
2. Preserva estructura: sheet names, headers, types
3. Detecta tablas (heurística: # columnas, # filas)
4. Por-sheet profiles: filas, headers, tipos

**Para CSV/XML/TXT**:
1. Parseo directo
2. CSV: infer delimiter (,|;|\t)

**Caching**:
- Hash SHA256 del archivo
- Serializa a JSON: text, pages, structured_data, sheet_profiles
- TTL: indefinido (versioned por OCR_EXTRACTION_CACHE_VERSION)

**Estimación de calidad**:
- `_estimate_text_quality()` → ratio de caracteres "extraños" (no ASCII, emojis, etc.)
- Si > threshold → "low_quality", sugiere retroceso al texto fallback

**Guardado**:
- `texto_ocr` en ImpDocumento
- `sheet_profiles_json` (per-sheet stats)
- page_texts (opcional, p/ lookup)

---

### Paso 4: Pre-clasificación (pre_classifier.py) — 5 capas

**Entrada**: filename, headers_norm, field_aliases (cargados), ocr_text, tenant_id

**L1 — Snapshot cache** (si recipe_snapshot_id preseleccionado):
- Carga cached_analysis del snapshot (si existe)
- Si doc_type + confidence válidos → `skip_ai=True`, retorna resultado completo

**L2 — Filename pattern**:
1. Normaliza filename: strip accents, dates, UUIDs, numbers
2. Busca en imp_filename_pattern (regex patterns, activos)
3. Si match: calcula confidence = base_confidence * (confirmed_count / total)
4. Si conf >= threshold (0.70 default) → doc_type hint, continúa a IA

**L3 — Header mapping**:
1. Normaliza headers extraídos del OCR / Excel
2. Mapea a canonical fields usando field_aliases (reverse map)
3. Calcula canonical_fields_hash (SHA256 de campos encontrados)
4. Busca en imp_header_doc_type
5. Si match + confirmed_count >= min (2) → doc_type hint, opcional skip IA si conf >= 0.75

**L4 — Vendor/RUC**:
1. Extrae RUC del ocr_text (regex patterns configurables, 8-15 dígitos)
2. Busca en imp_vendor_snapshot (tenant, ruc, confirmed_count >= 2)
3. Si match → usa recipe_snapshot del vendor, retorna snapshot_id hint (skip_ai=False pero IA usa hint)

**L5 — Template match**:
1. Carga imp_doc_type_template (tenant_id=NULL y tenant_id=this_tenant, activos)
2. Evalúa activacion_json:
   - filename_patterns (regex, OR)
   - text_keywords (AND, todo debe estar en ocr_text)
   - min_text_length
   - tipo_archivo permitidos
3. Si activación OK:
   - Extrae campos usando extraccion_json: regex (first match) + label_search
   - Valida campos_requeridos (si falta alguno → confidence=0.0)
   - Confidence = (campos extraídos / total campos definidos)
   - Si confidence >= min_confidence_para_skip (0.80 default) → `skip_ai=True`
   - Retorna extracted_fields como cached_analysis

**Retorna**:
```python
PreClassResult(
    doc_type=str,
    confidence=float,
    layer="snapshot_cache" | "filename_pattern" | "header_mapping" | "vendor_ruc" | "template",
    reasoning=str,
    skip_ai=bool,
    cached_analysis=dict | None,
    extracted_fields=dict | None
)
# O None si no aplica nada
```

---

### Paso 5: Llamada a IA (ai_classifier.py) — Condicional

**Si pre_classifier retornó skip_ai=True**:
- Usa cached_analysis como resultado final
- Salta a Step 7 (Routing)

**Si pre_classifier retornó skip_ai=False O None**:
- Llama `analyze_document()` (ai_classifier.py)
- Construye prompt:
  - System prompt: instrucciones generales
  - User prompt:
    - Contexto temporal (año actual, fechas locales)
    - Hint del doc_type pre-clasificado (si existe)
    - OCR text (primeros 20K chars)
    - Table preview (si hay tablas)
    - Hints de campos (si pre_classifier extrajo algunos)
- Modelo: `_resolve_model_for_doctype()` (configurable por doc_type)
- Parámetros: temperatura, max_tokens, etc. (runtime_config)
- Timeout: configurable

**Respuesta AI**:
- JSON parsing: {"doc_type": str, "fields": {}, "is_table": bool, "confidence": float, ...}
- Normaliza con `_normalize_analysis_output()` (analysis_normalizer.py)
- Aplica repairs: `_apply_high_evidence_ocr_repairs()` si OCR quality >= threshold

---

### Paso 6: Extracción de campos (processing_service.py + canonical_document.py)

**De cached_analysis O AI result**:
1. Mapea raw fields a canonical fields (usando field_aliases)
2. Normaliza valores:
   - Fechas → ISO 8601 (YYYY-MM-DD)
   - Montos → floats, parsea múltiples formatos (,. como decimal)
   - Text → strip, upper case (si es código), etc.
3. Construye canonical_document (diccionario normalizado)
4. Extrae metadatos:
   - proveedor_detectado
   - ruc_detectado
   - monto_total
   - moneda
   - fecha_documento
5. Para tablas:
   - `upsert_staging_lines_from_extraction()` → crea ImpStagingLine por línea
   - Estado inicial: PENDING (será validado/procesado después)

---

### Paso 7: Routing / Decisión de revisión (document_routing_agent.py)

**build_document_routing_decision**:
1. Resuelve tenant, sector
2. Busca ImpRoutingRule aplicables (por doc_type, categoría, tenant, sector)
3. Ordena por priority (ASC)
4. Itera rules hasta encontrar match:
   - source_key = doc_type OR category
   - Resuelve profile_code → ImpRoutingProfile
5. Valida required_groups (OR-groups de campos):
   - [["issue_date"], ["total_amount"], ["concept", "vendor"]]
   - Significa: issue_date OR (total_amount) OR (concept AND vendor)
6. Calcula campos faltantes
7. Decide:
   - Si required_groups OK + confidence >= threshold → needs_human_review=False
   - Si required_groups FAIL → needs_human_review=True
   - suggested_destination = profile.suggested_destination

**Retorna**:
```python
DocumentRoutingDecision(
    document_type=str,
    confidence=float,
    required_fields_ok=bool,
    missing_fields=[...],
    suggested_destination="recipe" | "expense" | "supplier_invoice" | None,
    reason=str,
    needs_human_review=bool
)
```

---

### Paso 8: Guardado en BD (crud.py + api_lifecycle.py)

**update_documento**:
- tipo_documento_detectado
- confianza_clasificacion
- requiere_revision (basado en routing decision)
- datos_extraidos (JSON)
- estado: REVIEW (si requiere_revision=True) O CONFIRMED (si no)
- llm_model (traceability)
- raw_ai_json (prompt + respuesta, para auditoría)
- recipe_snapshot_id (si se usó snapshot)

**Auditoría**:
- Crea ImpLogCambios con acción="CLASSIFY"

**Batch tracking**:
- `touch_batch_items_for_document()` → actualiza ImpBatchItem.estado
- `refresh_batch_status()` → recalcula ImpBatchImport.estado (PROCESSING → COMPLETED/PARTIAL)

---

### Paso 9: Staging lines (iteration_service.py)

**Para documentos con tablas**:
- Ya creadas en Step 6 con estado=PENDING
- El usuario puede:
  - Revisarlas (detail page)
  - Ejecutar iteraciones (reprocesamiento)
  - Marcar como SKIPPED o REVIEW

---

## 5. Backend — Sistema de aprendizaje

### ¿Qué aprende el sistema?

1. **Patrones filename** (classifier_learning.py):
   - Mapea nombre archivo → doc_type
   - Tabla: imp_filename_pattern
   - Ejemplo: "factura.*" → FACTURA_ELECTRONICA

2. **Header→doc_type mappings**:
   - Mapea conjunto de canonical fields → doc_type
   - Tabla: imp_header_doc_type
   - Ejemplo: {issue_date, total, vendor} → FACTURA

3. **Field aliases**:
   - Mapea nombres de columna (raw) → canonical field name
   - Tabla: imp_field_alias
   - Ejemplo: "Fecha de Emisión" → issue_date

4. **Vendor snapshots**:
   - Mapea RUC (o nombre vendor normalizado) → recipe snapshot
   - Tabla: imp_vendor_snapshot
   - Acelera L4 del pre-clasificador

5. **Template usage stats**:
   - Tracking de qué templates se usan y con qué éxito
   - Incrementa total_usos, total_exitosos en imp_doc_type_template

6. **Routing feedback**:
   - Guarda cada decisión humana (save, edit, reject) para análisis
   - Tabla: imp_routing_signal
   - Feed a document_routing_learning_insights_service

### Cuándo se activa el aprendizaje

**Trigger 1: Confirmación de documento**:
```
POST /documents/{id}/confirm (usuario confirma campos)
  ↓
crud.update_documento(estado=CONFIRMED, datos_confirmados={...})
  ↓
classifier_learning.learn_from_confirmation(
    doc_filename, doc_type_confirmed, pre_class_layer, headers_norm
)
  ↓
Aprende filename patterns, header mappings, field aliases
  ↓
Invalidate caché pre-clasificador (5 min TTL)
```

**Trigger 2: Save con destino**:
```
POST /documents/{id}/save → saved_as=expense/recipe/supplier_invoice
  ↓
snapshot_learning.bootstrap_learning_from_existing_document()
  ↓
Aprende vendor snapshot si RUC extraído
  ↓
remember_snapshot_learning() → guarda en snapshot_id
```

**Trigger 3: Iteraciones completadas**:
```
POST /staging-lines/iterate?scope=...
  ↓
iteration_service.close_iteration(improvement=True)
  ↓
Trigger documento_model_learning_service si hay mejora
```

### Tablas de almacenamiento

- **imp_filename_pattern**: pattern (regex), doc_type, base_confidence, confirmed_count, failed_count, source (hardcoded|learned)
- **imp_header_doc_type**: canonical_fields_hash (SHA256), doc_type, confirmed_count, failed_count
- **imp_field_alias**: canonical_field, alias, tenant_id (NULL=global), priority, source (hardcoded|learned), confirmed_count
- **imp_vendor_snapshot**: ruc, vendor_norm, recipe_snapshot_id, confirmed_count, active
- **imp_doc_type_template**: (visto arriba) incluyendo total_usos, total_exitosos

### Cómo afecta el aprendizaje a futuras importaciones

1. **En pre-clasificación**:
   - L2 (filename): confidence = base_confidence * (confirmed_count / total), si confirmed_count >= 3 sube weight
   - L3 (header): mapping encontrado si confirmed_count >= 2
   - L4 (vendor): vendor_snapshot activo si confirmed_count >= 2
   - L5 (template): tracking de éxito incrementa priority implícitamente

2. **En auto_recipe**:
   - `resolve_auto_recipe()` usa snapshot from learned vendor
   - `should_reprocess_existing_document()` detecta si hay learning updates pendientes
   - Si sí → auto-reenqueue con reprocess_mode="fast" (Trigger en batch_service)

3. **En feedback loop**:
   - `imp_routing_signal` registra cada decision
   - `document_routing_learning_insights_service` analiza patterns
   - Propone updates a `imp_routing_profile` (required_groups, confidence_threshold)

---

## 6. Backend — Reprocesado

### Diferencia entre modo `fast` y modo `deep`

#### Modo FAST (default)
- **Cuándo**: Re-processing de mismo documento con learning updates
- **Flujo**:
  1. Reutiliza recipe_snapshot si disponible (pre-selected)
  2. Salta directamente a L5 (templates) si es snippet + cached_analysis
  3. No vuelve a ejecutar pre-clasificación completa
  4. Reusa headers normalizados del anterior
  5. IA: Only if pre-classifier retorna skip_ai=False

- **Cuándo se salta IA**:
  - cached_analysis válido de snapshot → skip_ai=True
  - Template match con confianza >= threshold → skip_ai=True

#### Modo DEEP (full reprocessing)
- **Cuándo**: Usuario solicita "reiniciar análisis desde cero"
- **Flujo**:
  1. Descarta recipe_snapshot preseleccionado (fuerza recipe_snapshot_id=None)
  2. Corre pre-clasificación completa (todas 5 capas)
  3. Llama IA siempre (a menos que L5 template salte)
  4. Re-OCR si archivo disponible (reutiliza caché si existe)
  5. Re-learns desde cero

- **Cuándo se usa**:
  - Usuario hace click "Reprocess from scratch"
  - batch_service detecta reprocess_mode="deep"

### Condiciones del código para skip IA

**En pre_classifier.py**:
```python
if cached_analysis:
    # L1 snapshot cache
    if doc_type and confidence > 0:
        return PreClassResult(..., skip_ai=True, cached_analysis=...)

# ... L2, L3, L4 retornan skip_ai=False

# L5 template
skip = confidence >= min_skip  # default 0.80
return PreClassResult(..., skip_ai=skip, cached_analysis=cached if skip else None)
```

**En processing_service.py**:
```python
pre_class = classify_before_ai(...)
if pre_class and pre_class.skip_ai:
    # Usa cached_analysis como si fuera resultado AI
    ai_result = pre_class.cached_analysis
    proceed_to_extraction()
else:
    # Llama analyze_document()
    ai_result = await ai_classifier.analyze_document(...)
```

---

## 7. Frontend — Arquitectura de archivos

### `Panel.tsx`
**Responsabilidad**: Contenedor principal del módulo importador.

**Componentes/hooks usados**:
- Router (Routes.tsx)
- Layout wrapper
- Navigation

---

### `Routes.tsx`
**Responsabilidad**: Definición de rutas del módulo.

**Rutas principales**:
- `/` → Dashboard
- `/documents` → DocumentList
- `/documents/:id` → DocumentDetail
- `/recipes` → RecipeManager
- `/reprocess/:id` → ReprocessPanel

---

### `pages/Dashboard.tsx`
**Responsabilidad**: Resumen visual de importaciones.

**Contenido**:
- Stats: total, pendientes, en_revision, confirmados, fallidos
- Lotes recientes
- Documentos recientes
- Insights de aprendizaje

---

### `pages/ImportPage.tsx`
**Responsabilidad**: Upload de archivos y inicio de batch.

**Componentes**:
- QuickUploadPanel (drag-drop)
- BatchTracker (polling status)
- Handlers: upload, reprocess, recipe_selection

---

### `pages/DocumentDetail.tsx`
**Responsabilidad**: Detalle de un documento (campos extraídos, confirmación, edición).

**Funcionalidad**:
- Display: tipo detectado, confianza, routing decision
- Edición: edit_fields_request
- Confirmación: datos_confirmados
- Save: destination selection
- Review hints (campos sugeridos para revisar)
- Staging lines (si hay tabla)

---

### `pages/DocumentList.tsx`
**Responsabilidad**: Lista de documentos con filtros.

**Filtros**: estado, proveedor, monto, fecha, usuario

---

### `pages/ReprocessPanel.tsx`
**Responsabilidad**: Reprocesamiento iterativo de líneas.

**Funcionalidad**:
- `useImportReprocess` hook
- Summary (pending, valid, imported, invalid, review, skipped, reprocess)
- Load lines con filtros
- Inspect fields (análisis)
- Build review session (crear sesión de revisión)
- Execute iteration (correr reprocesamiento)
- Patch individual lines

---

### `components/ImportIntake.tsx`
**Responsabilidad**: Componente de drag-drop y selección de receta.

**Props**:
- onUpload(files, recipeSnapshot?, reprocessMode?)
- isLoading, error

---

### `components/SaveDocumentModal.tsx`
**Responsabilidad**: Modal para guardar documento (destination, payment, warehouse, line matches).

**Props**:
- documentId
- onSave(request)
- isLoading

---

### `components/SaveProductsModal.tsx`
**Responsabilidad**: Modal para crear productos desde documento.

---

### `components/QuickUploadPanel.tsx`
**Responsabilidad**: Upload rápido (visible en dashboard).

---

### `hooks/useImportReprocess.ts`
**Responsabilidad**: Hook para reprocesamiento iterativo (leído arriba completamente).

**State**:
- summary (StagingLineSummary)
- lines (StagingLine[])
- iterations (IterationRecord[])
- activeSession, lastResult
- isRunning, isLoading, error

**Methods**:
- refreshSummary()
- loadLines(params)
- inspectFields(estados, errorCodes, sheet)
- loadIterations()
- buildReviewSession(filters)
- executeSession(sessionId)
- iterate(scope)
- markForReprocess(lineIds, campos)
- correctLine(lineId, normalizedData, campos)

---

### `services.ts`
**Responsabilidad**: API calls para importador.

**Funciones principales**:
- uploadDocuments(files, ...)
- fetchDocumento(id)
- confirmDocumento(id, datos_confirmados)
- editFields(id, campos)
- saveDocument(id, request)
- saveProducts(id, request)
- saveRecipe(id)
- reprocessDocument(id, mode)
- fetchBatch(id), listBatches()
- fetchStagingLines(), fetchStagingSummary()
- fetchIterations()
- runIteration(), runReviewSession()
- patchStagingLine(), bulkPatchStagingLines()
- fetchFieldAnalysis()

---

### `constants.ts`
**Responsabilidad**: Constantes frontend.

**Contenido**:
- Estados enum (PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED)
- Tipos documento
- Colores, labels

---

### `manifest.ts`
**Responsabilidad**: Metadatos del módulo (rutas, permisos, iconos).

---

## 8. Frontend — Flujo de usuario (UX)

### 1. Upload de archivos

```
Usuario:
  1. Navigate a /importador
  2. Drag-drop archivos o click "Select files"
  3. Opcional: preseleccionar recipe snapshot
  4. Click "Upload"
  ↓
Frontend (ImportPage.tsx):
  5. POST /documents/upload { files, recipe_snapshot_id?, reprocess_mode? }
  6. Poll GET /batches/{batch_id} cada 2s
  7. Display progress (pending, processing, completed items)
  ↓
Backend:
  8. batch_service.enqueue_async_batch()
  9. Celery tasks queued
  10. Poll returns: total_items, completed_items, completed_at
  ↓
Usuario:
  11. Cuando batch completa → "Review documents"
```

### 2. Espera (polling / websocket)

**Actualmente**: HTTP polling cada 2 segundos

**En services.ts**:
```typescript
async fetchBatch(batchId) {
  // GET /batches/{batchId}
  // Returns: BatchDetailOut (id, estado, items[], progress_pct)
}
```

**En DocumentList / Dashboard**:
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    refreshBatch();
  }, 2000);
  return () => clearInterval(interval);
}, [batch_id]);
```

### 3. Revisión del resultado

```
Usuario navega a DocumentDetail:
  1. GET /documents/{id} → DocumentoOut
  2. Display:
     - tipo_documento_detectado + confianza
     - routing_decision (destination, missing_fields)
     - datos_extraidos (visualización)
     - review_hints (campos sugeridos para revisar)
     - assisted_review (si hay tabla)
  3. Si requiere_revision=True → "Please review fields below"
  4. Si hay tabla → mostrar staging_lines
```

### 4. Acciones disponibles

#### a. **Confirmar campos**
```
POST /documents/{id}/confirm
{
  "datos_confirmados": { "campo1": valor, ... }
}
→ Triggers classifier_learning
→ estado = CONFIRMED
```

#### b. **Editar campos**
```
PATCH /documents/{id}
{
  "campos": { "field1": new_value, ... }
}
→ Actualiza datos_confirmados
→ Log: acción="EDIT"
```

#### c. **Guardar en destino**
```
POST /documents/{id}/save
{
  "destination": "expense" | "recipe" | "supplier_invoice",
  "payment_status": "pending" | "partial" | "paid",
  "line_matches": [ { line_index, product_id, persist_alias } ],
  ...
}
→ saved_as, saved_record_id, saved_at
→ Crea recurso en destino (Expense, Recipe, PurchaseOrder)
→ Log: acción="SAVE"
```

#### d. **Reprocess (iterativo)**
```
Navegamos a ReprocessPanel:
  1. useImportReprocess(documentoId)
  2. refreshSummary() → StagingLineSummary (pending, valid, imported, invalid, review, reprocess)
  3. loadLines() → StagingLine[] (raw_data, normalized_data, estado, error_detail)
  4. Usuario puede:
     a. Mark for reprocess: bulkPatchStagingLines(lineIds, "REPROCESS")
     b. Correct manually: patchStagingLine(lineId, { normalized_data, campos_revision })
     c. Inspect by field: fetchFieldAnalysis() → qué campos tienen errores
     d. Run iteration: runIteration(scope) → reenqueue en Celery
  5. Poll: loadIterations() cada 3s
  6. Resultado: iteration result (lines_imported, lines_errored, improvement bool)
```

#### e. **Reject**
```
Documento en estado REVIEW pero usuario rechaza:
  POST /documents/{id}/reject
  → estado = FAILED
  → Log: acción="REJECT"
```

### 5. Estados del documento

```
PENDING
  ↓ (procesamiento comienza)
PROCESSING
  ├─ (pre-class + AI + routing)
  ├─→ Si requiere_revision=True
  │     ↓
  │     REVIEW (espera confirmación)
  │       ├─→ confirm() → CONFIRMED
  │       ├─→ edit() → REVIEW (resubmit)
  │       ├─→ save() → saved_at, puede quedar en CONFIRMED/REVIEW
  │       └─→ reject() → FAILED
  │
  └─→ Si requiere_revision=False
        ↓
        CONFIRMED (auto-guardable)
          └─→ save() → saved_at

FAILED
  (OCR error, timeout, parsing error)
  └─→ Pode reuploadse → PENDING
```

---

## 9. Configuración runtime

### ¿Qué parámetros son configurables en runtime?

Todos almacenados en tabla `imp_config` (module, key, value_text|value_list).

**Módulos principales**:

#### `pre_classifier`:
- `min_header_confirmations` (int, default 2)
- `filename_min_confidence` (float, default 0.70)
- `header_coverage_min_ratio` (float, default 0.50)
- `structured_skip_threshold` (float, default 0.75)
- `ocr_weird_ratio_max` (float, default 0.15)

#### `ocr`:
- `pdf_render_dpi` (int, default 300)
- `image_contrast` (float, default 1.8)
- `image_sharpness` (float, default 2.0)
- `tesseract_languages` (list, default ["spa", "eng"])
- `min_width` (int, default 1800)
- `weak_text_min_words`, `weak_text_min_chars`

#### `classification`:
- `confidence_threshold` (float, default 0.85)
- `ai_model` (str, routing de modelos por doc_type)

#### `learning`:
- `event_weight_save` (float, default 4.0)
- `event_weight_confirm` (float, default 3.0)
- `event_weight_edit` (float, default 1.35)
- `quality_bonus_required_fields_ok` (float, default 0.75)
- `filename_pattern_base_confidence` (float, default 0.65)

#### `file_support`:
- `accepted_extensions` (list)
- `image_extensions` (list)

#### `cache_ttls`:
- `pre_classifier_ttl_seconds` (int, default 300)
- `field_aliases_ttl_seconds` (int, default 300)

#### `limits`:
- `max_queue_per_tenant` (int, env var IMPORTADOR_MAX_QUEUE_PER_TENANT)
- `max_files_per_request` (int, env var IMPORTADOR_MAX_FILES_PER_REQUEST)
- `max_file_size_mb` (int, env var IMPORTS_MAX_FILE_SIZE_MB)
- `max_upload_mb` (int, env var IMPORTS_MAX_UPLOAD_MB)

### Defaults más importantes

(En runtime_config.py):
- Ocr: DPI 300, contrast 1.8, sharpness 2.0
- Pre-classifier: confidence 0.70, coverage ratio 0.50
- Learning: event weights (save 4x, confirm 3x, edit 1.35x)
- File support: 15 extensiones soportadas

### Cómo se sobreescriben

1. **Environment variables** (prioridad 1):
   ```bash
   IMPORTADOR_MAX_FILES_PER_REQUEST=200
   IMPORTS_MAX_FILE_SIZE_MB=32
   ```

2. **imp_config tabla** (prioridad 2):
   ```sql
   INSERT INTO imp_config (module, key, value_text)
   VALUES ('ocr', 'pdf_render_dpi', '600');
   ```

3. **Hardcoded defaults** (prioridad 3):
   ```python
   _DEFAULT_OCR_CONFIG = { "pdf_render_dpi": 300, ... }
   ```

**Caching**: 300 segundos por defecto. Invalidar:
```python
# En código
from app.modules.importador.pre_classifier import invalidate_pre_classifier_cache
invalidate_pre_classifier_cache()  # Fuerza reload en próxima llamada
```

---

## 10. Tests existentes

### Archivos de test (en /c/gestiqcloud/apps/backend/app/tests/)

| Test File | Cobertura | Estado |
|-----------|-----------|--------|
| test_importador_batch_service.py | Batch queueing, dedup, reprocess logic | ✓ Activo |
| test_importador_processing_service.py | Full pipeline: OCR→pre-class→AI→routing | ✓ Activo |
| test_importador_ai_classifier.py | AI calling, prompt building, output normalization | ✓ Activo |
| test_importador_ocr_service.py | PDF render, image OCR, Excel parsing, caching | ✓ Activo |
| test_importador_doc_type_resolution.py | Doc type fallback extraction | ✓ Activo |
| test_importador_iteration_service.py | Staging lines, reprocessing iterations | ✓ Activo |
| test_importador_edit_line_items.py | Line item patching, bulk ops | ✓ Activo |
| test_importador_product_import_service.py | Product sync from document | ✓ Activo |
| test_importador_recipe_router.py | Recipe CRUD endpoints | ✓ Activo |
| test_importador_routing_admin_api.py | Routing profile + rule admin | ✓ Activo |
| test_importador_routing_feedback.py | Routing signal recording | ✓ Activo |
| test_importador_document_routing.py | Routing decision logic | ✓ Activo |
| test_importador_runtime_config.py | Config loading + caching | ✓ Activo |
| test_importador_async_learning.py | Classifier learning loops | ✓ Activo |
| test_importador_admin_service_helpers.py | Admin utilities | ✓ Activo |
| test_importador_supplier_invoice_flow.py | End-to-end supplier invoice | ✓ Activo |
| test_importador_tasks_learning.py | Learning from Celery tasks | ✓ Activo |
| test_importador_upload_learning.py | Upload batch learning | ✓ Activo |
| test_importador_tenant_scope.py | Multi-tenant isolation | ✓ Activo |
| test_importador_utils.py | Utility functions | ✓ Activo |
| test_importador_purge_all.py | Data cleanup | ✓ Activo |

### Frontend tests

| Test File | Cobertura | Estado |
|-----------|-----------|--------|
| services.test.ts | API calls mocking | ✓ Activo |
| DocumentDetail.groups.test.ts | Grouping logic for review | ✓ Activo |
| ImportPage.test.tsx | Upload + batch flow | ✓ Activo |
| SaveDocumentModal.test.tsx | Save modal logic | ✓ Activo |

### Qué está bien cubierto

✓ Batch queueing y deduplicación
✓ OCR extracción (PDF, imágenes, Excel)
✓ Pre-clasificación (5 capas)
✓ AI prompting y output parsing
✓ Routing decision logic
✓ Staging lines y iteraciones
✓ Classifier learning (filename, header, aliases)
✓ Multi-tenant isolation
✓ API lifecycle (upload, confirm, edit, save)

### Qué falta cubrir

- [ ] Performance tests (documentos grandes, tablas complejas)
- [ ] Integration tests (end-to-end con IA real)
- [ ] Error recovery (OCR timeout, AI unavailable, DB errors)
- [ ] Concurrent batch processing (race conditions)
- [ ] Template matching edge cases (overlapping templates)
- [ ] Frontend E2E tests (Playwright/Cypress)
- [ ] Snapshot learning consistency (cross-tenant)
- [ ] Vendor snapshot deduplication (múltiples RUC, mismo nombre)
- [ ] Routing config migrations (cambio de rules en producción)
- [ ] Memory usage (archivos muy grandes, OCR cache unbounded)

---

## Anexo: Tablas de referencia

### Estados de documentos

| Estado | Significado | Transiciones posibles |
|--------|-------------|----------------------|
| PENDING | Encolado, sin procesar | → PROCESSING |
| PROCESSING | Procesándose actualmente | → REVIEW \| CONFIRMED \| FAILED |
| REVIEW | Requiere revisión humana | → CONFIRMED \| FAILED \| REVIEW (edit) |
| CONFIRMED | Confirmado por usuario | → (guardable) |
| FAILED | Error irreversible | → PENDING (reupload) |

### Estados de staging lines

| Estado | Significado | Transiciones |
|--------|-------------|--------------|
| PENDING | No procesada | → VALID \| INVALID \| REVIEW \| SKIPPED |
| VALID | Validada, lista para importar | → IMPORTED |
| IMPORTED | Importada al destino | (final) |
| INVALID | Error de validación | → REPROCESS \| SKIPPED |
| REVIEW | Requiere revisión | → REPROCESS \| SKIPPED \| IMPORTED |
| SKIPPED | Ignorada | (final) |
| REPROCESS | Marcada para reprocesamiento | → VALID \| INVALID \| REVIEW |

### Acciones auditadas (imp_log_cambios.accion)

| Acción | Cuándo | Detalle típico |
|--------|--------|----------------|
| UPLOAD | Archivo subido | filename, size, batch_id |
| CLASSIFY | Pre-clasificación | doc_type, layer, confidence |
| EXTRACT | Extracción de campos | field_count, model_used |
| VALIDATE | Validación routing | required_ok, missing_fields |
| CONFIRM | Usuario confirma | datos_confirmados (subset) |
| EDIT | Usuario edita campos | campos_editados, old→new |
| SAVE | Guardado en destino | destination, saved_record_id |
| REJECT | Rechazo de documento | reason |
| REPROCESS | Reprocesamiento | iteration_num, scope |
| SKIP_DUPLICATE | Deduplicación | reason (same hash, etc.) |

---

**Documento generado el 10 de abril de 2026.**
**Módulo Importador v1.3 - GestiqCloud**
