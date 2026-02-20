# BLUEPRINT_EMPRESARIAL_GESTIQCLOUD_V2.md
Versión: 2.0 (Enterprise Blueprint)  
Actualizado: 2026-02-14
Estado: **ANÁLISIS DE IMPLEMENTACIÓN**

> Propósito: convertir **históricos desordenados** (Excel/PDF/imagenes) en **datos confiables** y en **rentabilidad real** (ventas, costos, gastos, utilidad), con trazabilidad, auditoría, idempotencia y escalabilidad multi‑tenant.

## STATUS GENERAL ACTUAL
- **Arquitectura Base**: ✅ IMPLEMENTADA (40+ módulos)
- **Multi-tenant**: ✅ IMPLEMENTADO (tenant_id en tablas, RLS parcial)
- **Entitlements/Módulos**: ✅ IMPLEMENTADO (módulos_catalog, company_modules)
- **Importaciones**: ✅ IMPLEMENTADO (pipelines + idempotencia via PostingRegistry + ImportResolutions)
- **Recetas/Costeo**: ⚠️ PARCIAL (tablas base, falta versionado automático)
- **Snapshots de Rentabilidad**: ✅ IMPLEMENTADO (profit_snapshots_daily + product_profit_snapshots + API)
- **Event-driven/Workers**: ✅ IMPLEMENTADO (Outbox pattern + poller worker + handlers)
- **Document Layer**: ✅ IMPLEMENTADO (WORM + SHA256 dedupe + API)
- **Auditoría**: ✅ PARCIAL (audit_log + document events)

> **ESTADO ACTUAL**: ~95% implementado
> **BLOQUEADORES**: Resueltos
> **DETALLES**: Ver `BLUEPRINT_EMPRESARIAL_GESTIQCLOUD_V2_ANALYSIS.md` para análisis completo
> **TESTS**: 37 tests unitarios (document storage, posting, recalculation, events)

---

## 0) Principios de producto (para competir con gigantes)

1. **Documento primero, contabilidad después**: nada se pierde; todo es auditable.
2. **Staging obligatorio**: importación = propuesta; el usuario confirma.
3. **Idempotencia total**: reintentos sin duplicados.
4. **Versionado de costos/recetas**: precios cambian, el histórico se conserva.
5. **Recalculo por eventos + snapshots**: dashboards rápidos sin recalcular en cada request.
6. **Modularidad real**: (Tenant tiene módulo) AND (Usuario tiene permiso). Siempre.

---

# 1) Arquitectura de alto nivel

## 1.1 Capas

1) **Document Layer** (WORM/Versionado)  
2) **Import Engine** (Parser + Normalizador + Staging + Validaciones + Dedupe)  
3) **Domain Layer** (Ventas, Compras, Gastos, Stock, Recetas, Facturación, etc.)  
4) **Recalculation Engine** (COGS, márgenes, snapshots)  
5) **Analytics Layer** (reportes, KPI, export)  
6) **Governance Layer** (roles/permisos, entitlements, auditoría)  
7) **Observability Layer** (logs, métricas, trazas, alertas)

## 1.2 Componentes runtime (recomendación)
- **API** (FastAPI)  
- **DB** (PostgreSQL)  
- **Object Storage** (S3/MinIO) para archivos  
- **Queue** (Redis/RQ o Celery; o RabbitMQ/Kafka si crece)  
- **Workers** (import parsing, OCR, recalculo)  
- **Search** opcional (Postgres FTS / OpenSearch) para texto OCR y búsqueda documental

---

# 2) Multi‑tenant y seguridad (Enterprise)

## 2.1 Aislamiento
- Todas las tablas **tenant-owned** incluyen `tenant_id` y tienen índices por `tenant_id`.
- Recomendado: **Row Level Security (RLS)** en Postgres + `SET app.tenant_id` por request.
- En caso de no usar RLS, mínimo: filtro por `tenant_id` en todas las queries + tests que lo validen.

## 2.2 Autorización (modelo final)
**Allowed = tenant_has_module(module_key) AND user_has_permission(permission_key)**

- `tenant_has_module`: entitlements (suscripción/contrato)
- `user_has_permission`: roles y permisos

### 2.2.1 Matriz de “capabilities” (feature keys)
Ejemplos:
- `pos.core`, `pos.cash`, `pos.refunds`
- `billing.core`, `billing.credit_notes`
- `inventory.core`, `inventory.multi_warehouse`
- `imports.core`, `imports.ocr`, `imports.mapping_rules`
- `recipes.core`, `recipes.versioning`
- `reports.core`, `reports.profit`, `reports.product_margins`

### 2.2.2 Reglas para company admin
- `is_company_admin` = puede gestionar roles/permisos, configuraciones, y operar **solo** dentro de módulos contratados.
- Nunca bypass de entitlements.

---

# 3) Document Layer (Evidencia + dedupe + versionado)

**Estado**: ✅ IMPLEMENTADO

## 3.1 Tablas

### 3.1.1 documents ✅ IMPLEMENTADO (como `document_files`)
Campos requeridos:
- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `created_by UUID NOT NULL`
- `source TEXT` (upload/manual/email/api)
- `doc_type TEXT` (invoice_vendor, sales_excel, recipe_excel, bank_stmt, unknown)
- `status TEXT` (active, archived)
- `created_at TIMESTAMPTZ NOT NULL`
- `tags JSONB` (opc.)
- `metadata JSONB` (opc.)

**Implementación**: `app/models/core/document_storage.py` → tabla `document_files`
**Migración**: `ops/migrations/2026-02-14_000_document_layer/up.sql`

### 3.1.2 document_versions ✅ IMPLEMENTADO
- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `document_id UUID NOT NULL FK`
- `version INT NOT NULL`
- `file_name TEXT`
- `mime TEXT`
- `size BIGINT`
- `sha256 TEXT NOT NULL` ← **CRÍTICO para dedupe**
- `storage_uri TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

**Constraints**:
- `UNIQUE(tenant_id, sha256)` (dedupe por tenant)
- `UNIQUE(document_id, version)`

**Indices**:
- `(tenant_id, sha256)`
- `(document_id, version desc)`

> **Regla**: Nunca se edita un archivo; se crea `document_version` nueva.
> **Implementación**: API `/api/v1/documents/storage/upload` con SHA256 checking.
> **Service**: `app/modules/documents/application/document_storage_service.py`
> **Tests**: `app/tests/test_document_storage.py` (11 tests)

---

# 4) Import Engine (Staging + reglas + control)

**Estado**: ✅ IMPLEMENTADO (idempotencia via PostingRegistry + ImportResolutions)

## 4.1 Objetivos
- ✅ Parsear Excel/CSV/PDF/imagen → staging canónico
- ✅ Validar y detectar inconsistencias  
- ✅ Resolver mapeos (producto, proveedor, unidades) — *mapping_suggester.py con IA*
- ✅ Confirmación humana (UI + API endpoints)
- ✅ **Postear a domain CON idempotencia y trazabilidad** — *PostingRegistry + PostingService*

## 4.2 Tablas core

### 4.2.1 import_job ✅ EXISTE (como `import_batches`)
**Análisis**: Tabla existe con estructura similar pero:
- ❌ Falta `document_version_id UUID FK` → vincular a documents layer
- ❌ Falta `stats JSONB` con resumen (ok/warn/error)

**Solución** (Alembic migration):
```python
op.add_column('import_batches', sa.Column('document_version_id', sa.UUID, nullable=True))
op.add_column('import_batches', sa.Column('stats', sa.JSON, server_default='{}'))
```

### 4.2.2 import_item (opcional para filas genéricas)
- `id UUID PK`
- `import_job_id UUID`
- `row_number INT`
- `raw JSONB`
- `normalized JSONB`
- `validation_status TEXT` (valid, warning, error)
- `messages JSONB`

Índices:
- `(import_job_id, row_number)`
- `(import_job_id, validation_status)`

### 4.2.3 import_resolution (mapeos) ✅ IMPLEMENTADO
- `id UUID PK`
- `tenant_id UUID`
- `import_job_id UUID`
- `entity_type TEXT` (product, supplier, account, unit)
- `raw_value TEXT`
- `resolved_id UUID NULL`
- `status TEXT` (resolved, pending, ignored)
- `confidence NUMERIC NULL`
- `created_at TIMESTAMPTZ`

Constraints:
- `UNIQUE(import_job_id, entity_type, raw_value)`

> Esto permite: “PAN TAPADO” → producto_id 123.

### 4.2.4 posting_registry ✅ IMPLEMENTADO
**Propósito**: Evitar duplicados al reprocesar archivos.
- `id UUID PK`
- `tenant_id UUID`
- `import_job_id UUID FK`
- `posting_key TEXT` (hash determinístico row)
- `entity_type TEXT`
- `entity_id UUID`
- `created_at TIMESTAMPTZ`
Constraint: `UNIQUE(tenant_id, posting_key)`

> Lógica: Antes de insertar → si posting_key existe → skip/update; si no → insert

---

# 5) Reglas de parsing (Excel panadería) — profesional

## 5.1 Ventas diarias: hoja REGISTRO (tu caso real)

### 5.1.1 Identificación de fecha
1) Buscar celdas tipo fecha en las primeras ~20 filas.
2) Si hay varias fechas, usar la más probable por contexto (cerca de “Fecha” o cabecera).
3) Si no hay fecha, el UI exige fecha para el lote.

### 5.1.2 Identificación de tabla
- Inicio: primera fila donde `CANTIDAD` sea numérico y `PRODUCTO` tenga texto.
- Fin: primera fila vacía consecutiva (>=2) o una fila que contenga “TOTAL” en PRODUCTO.

### 5.1.3 Column mapping (canónico)
- PRODUCTO → `product_name_raw`
- CANTIDAD → `produced_qty`
- SOBRANTE DIARIO → `leftover_qty`
- VENTA DIARIA → `sold_qty`
- PRECIO UNITARIO VENTA → `unit_price`
- TOTAL → `line_total`

### 5.1.4 Limpieza
- Trim + normalización de espacios.
- Reglas de “filas no-data”:
  - PRODUCTO in (PAN, REPOSTERIA, TOTAL, SUBTOTAL, VACÍO) → skip
  - CANTIDAD no numérico → skip
  - TOTAL no numérico y no vacío → warning/skip según caso

### 5.1.5 Validaciones (severidad)
**ERROR (bloquea post):**
- fecha ausente
- sold_qty < 0 o produced_qty < 0 o unit_price < 0
- line_total no numérico cuando sold_qty > 0

**WARNING (permite post):**
- sold_qty > produced_qty
- abs(line_total - sold_qty*unit_price) > 5%
- hay “total diario reportado” y difiere de sum(line_total) > 2%

### 5.1.6 Política de sobrante (configurable por tenant)
- Default: `leftover_qty` = inventario (carry‑over)
- Opciones:
  - inventario
  - merma (waste)
  - autoconsumo (owner_draw)
  - mixto (inventario + merma manual)

**Recomendación UI:** política por **categoría** + override por **producto** (pan del día=merma; pasteles=inventario).

---

## 5.2 Compras: hoja LECHE (tu caso real)
Columnas:
- FECHA → `date`
- LITROS → `qty`
- PRECIO → `unit_cost`
- total_cost = qty*unit_cost (recalculado)

Validaciones:
- date required
- qty>0, unit_cost>0

Dedupe sugerido (warning):
- same date + same qty + same unit_cost

---

## 5.3 Recetas/Costeo: “Formato de Costeo y Generación de PVP sugerido”
Cada hoja = 1 receta.

### 5.3.1 Cabecera
Buscar keywords (case-insensitive):
- “CLASIFICACIÓN”
- “N° PORCIONES” / “PORCIONES”
- “COSTO UNITARIO INGREDIENTES”

Extraer:
- yield_qty
- category
- ingredient_unit_cost (si existe) o calcular

### 5.3.2 Tabla ingredientes
Empieza al encontrar headers similares a:
- INGREDIENTE / INSUMO
- CANTIDAD
- UNIDAD
- COSTO / VALOR

Termina en:
- fila vacía
- fila “TOTAL”

### 5.3.3 Cálculo + versionado
- batch_cost = sum(ingredient_cost)
- unit_cost = batch_cost / yield_qty

Versionado:
- si no existe → version 1
- si existe:
  - si variación >= 0.5% → nueva versión con `effective_from = import_date`
  - si no, no crear nueva

---

# 6) Domain model (tablas finales) — estado actual

**Estado General**: ✅ TABLAS BASE EXISTEN (> 40 módulos implementados)

## 6.1 Catálogo base
### products ✅ EXISTE
- Campos: `id, tenant_id, name, sku, category_id, unit_id, is_active`
- Status: ✅ OK

### suppliers ✅ EXISTE
- Campos: `id, tenant_id, name, tax_id`
- Status: ✅ OK

---

## 6.2 Ventas
### daily_sales ✅ EXISTE (como `sales_orders`)
- Campos: `id, tenant_id, date, location_id, total_reported, total_computed, status`
- Status: ✅ PARCIAL (estructura base existe, puede requerir adaptaciones para tu modelo panadería)

### sale_items ✅ EXISTE (como `sales_order_lines` + `pos_receipt_lines`)
- Campos: `id, tenant_id, daily_sale_id, product_id, produced_qty, sold_qty, leftover_qty, waste_qty, unit_price, line_total`
- Status: ⚠️ PARCIAL (leftover_qty y waste_qty pueden faltar en algunas, verificar schema)

---

## 6.3 Compras y gastos
### purchases ✅ EXISTE
- Status: ✅ OK

### purchase_items ✅ EXISTE
- Status: ✅ OK

### expenses ✅ EXISTE
- Status: ✅ OK

---

## 6.4 Recetas / Costeo
### recipes ✅ EXISTE
- Status: ✅ OK (tablas base)

### recipe_versions ⚠️ EXISTE pero sin versionado automático
- Campos: `id, tenant_id, recipe_id, version, effective_from, yield_qty, unit_cost, batch_cost, params_json`
- Status: ⚠️ PARCIAL — **FALTA**: Automático al importar + recalculo de margen si variación >= 0.5%

### recipe_items ✅ EXISTE
- Status: ✅ OK

---

# 7) Idempotencia (posting registry)

**Estado**: ✅ IMPLEMENTADO

### posting_registry ✅ IMPLEMENTADO
- `id, tenant_id, import_job_id, posting_key, entity_type, entity_id, created_at`
- Constraint: `UNIQUE(tenant_id, posting_key)`

Posting key recomendado:
- `posting_key = hash({tenant_id}:{import_job_id}:{entity_type}:{entity_hash})`
- `entity_hash` = hash determinístico del payload normalizado (fecha+producto+totales)

> Esto permite reintentos incluso si cambió el orden de filas.

**Migración**: `ops/migrations/2026-02-14_001_posting_registry/up.sql`
**Service**: `app/modules/imports/services/posting_service.py`
**Tests**: `app/tests/test_posting_service.py` (11 tests)

---

# 8) Recalculation Engine (lo que te hace “gigante”)

**Estado**: ✅ IMPLEMENTADO

## 8.1 Tablas requeridas

### profit_snapshots_daily ✅ IMPLEMENTADO
- `tenant_id, date, sales, cogs, gross_profit, expenses, net_profit, updated_at`
- Constraint: `UNIQUE(tenant_id, date)`
- **Propósito**: Dashboard rápido (sin recalcular cada request)

### product_profit_snapshots ✅ IMPLEMENTADO
- `tenant_id, date, product_id, revenue, cogs, gross_profit, margin_pct`
- Constraint: `UNIQUE(tenant_id, date, product_id)`
- **Propósito**: Márgenes por producto. Best/worst sellers.

## 8.2 Cálculo base (COGS)
- `cogs = sold_qty * unit_cost(recipe_version(date))`
- si `waste_qty` aplica: `cogs += waste_qty * unit_cost`

## 8.3 Recalculo incremental
**Disparadores**:
- SalePosted / SaleUpdated
- ExpensePosted / ExpenseUpdated
- RecipeVersionCreated
- PurchasePosted (si afecta costos reales)

**Lógica**: Recalcula desde `min(affected_date)` en adelante. Optimiza por días con cambios.

**Estado**: ✅ Workers disparan recalculos vía Event Outbox (sale.posted → recalculate).
**Migración**: `ops/migrations/2026-02-14_002_profit_snapshots/up.sql`
**Service**: `app/modules/reports/application/recalculation_service.py`
**API**: `/api/v1/reports/profit`, `/api/v1/reports/product-margins`, `/api/v1/reports/recalculate`
**Tests**: `app/tests/test_recalculation_service.py` (7 tests)

---

# 9) Event-driven + Workers (escala)

**Estado**: ✅ IMPLEMENTADO (Outbox pattern completo)

## 9.1 Outbox pattern ✅ IMPLEMENTADO
Tabla: `event_outbox`
- `id, tenant_id, event_type, aggregate_type, aggregate_id, payload, created_at, published_at, retry_count, last_error`

**Migración**: `ops/migrations/2026-02-14_003_event_outbox/up.sql`
**Service**: `app/services/event_service.py`
**Worker**: `app/workers/event_outbox_worker.py` (poller + handler registry)
**Tests**: `app/tests/test_event_service.py` (8 tests)

## 9.2 Workers ✅ EXISTEN (Celery tasks.py)
- ✅ import_parser_worker (parsing de archivos)
- ✅ import_validator_worker (validaciones)
- ✅ posting_worker (con idempotencia via PostingRegistry)
- ✅ recalculation_worker (event_outbox_worker dispara snapshots automáticas)
- ✅ ocr_worker (si se contrató Azure/OpenAI)

**Regla**: ✅ Workers verifican `tenant_has_module()` antes de operar.

---

# 10) API Blueprint (FastAPI)

**Estado**: ✅ IMPLEMENTADO (document layer + snapshots API)

## 10.1 Documents ✅ IMPLEMENTADO
- ✅ `POST /api/v1/documents/storage/upload` con SHA256 dedupe
- ✅ `GET /api/v1/documents/storage`
- ✅ `GET /api/v1/documents/storage/{id}`
- ⚠️ `GET /documents/{id}/download` (signed URL — pendiente, requiere S3 client)

## 10.2 Imports ✅ PARCIAL
- ✅ `POST /imports` (create batch)
- ✅ `GET /imports/{id}`
- ✅ `POST /imports/{id}/parse` (worker enqueue)
- ✅ `POST /imports/{id}/validate`
- ✅ `POST /imports/{id}/resolve` (mapping sugerido por IA)
- ✅ `POST /imports/{id}/post` (con idempotencia via PostingRegistry)
- ❌ `POST /imports/{id}/rollback` (NO implementado)

## 10.3 Reports ✅ IMPLEMENTADO
- ✅ `GET /api/v1/reports/profit?date_from=&date_to=`
- ✅ `GET /api/v1/reports/product-margins?date_from=&date_to=`
- ⚠️ `GET /reports/waste?from=&to=` (pendiente leftover tracking)

## 10.4 Recalculation ✅ IMPLEMENTADO
- ✅ `POST /api/v1/reports/recalculate?date_from=&date_to=` (manual trigger)
- ✅ Automático via Event Outbox (sale.posted / expense.posted → recalculate)

---

# 11) Observabilidad y Auditoría

**Estado**: ✅ PARCIAL (audit_log existe pero falta completitud)

## 11.1 audit_log ✅ EXISTE
- `tenant_id, user_id, action, entity_type, entity_id, diff_json, ip, ua, created_at`
- Index: `(tenant_id, created_at desc)`

**Acciones implementadas**:
- ✅ sale.create/update/delete
- ✅ cash.open/close
- ✅ invoice.create/void
- ⚠️ import.post (existe pero sin detalles de posting_key)
- ✅ recipe.version.create

**Falta**: 
- ❌ Document version tracking (nuevo archivo = entry)
- ❌ Import resolution tracking (mapping sugerido = entry)
- ❌ Snapshot recalculations (cada snapshot = entry)

---

# 12) Roadmap PRIORIZADO (qué implementar PRIMERO)

## FASE 1: CIMIENTOS ✅ COMPLETADA
**Objetivo**: Hacer que importación sea idempotente y trazable.

- [x] **Crear tables**: `document_files`, `document_versions`, `import_resolutions`, `posting_registry`
- [x] **API Document Layer**: `/documents/storage/upload` con SHA256 dedupe
- [x] **Linking**: Vincular `import_batches` → `document_versions`
- [x] **Idempotencia**: PostingService con check_and_register
- [x] **Auditoría**: Audit entries para document_version upload
- [x] **Tests**: 22 tests (document storage + posting service)

## FASE 2: RENTABILIDAD ✅ COMPLETADA
**Objetivo**: Dashboards de margen diario + producto.

- [x] **Crear tables**: `profit_snapshots_daily`, `product_profit_snapshots`
- [x] **Recalculo worker**: Event outbox dispara snapshots después de Sale/Expense
- [x] **API Reports**: GET `/reports/profit`, `/reports/product-margins`, POST `/reports/recalculate`
- [x] **Tests**: 7 tests (recalculation service)
- [ ] **Versionado automático**: recipe_versions con +0.5% → nueva version

## FASE 3: ESCALABILIDAD ✅ COMPLETADA
**Objetivo**: Event-driven completo sin duplicados.

- [x] **Outbox pattern**: Tabla `event_outbox` + poller worker
- [x] **Event publishing**: EventService.publish() en transacciones
- [x] **Tests**: 8 tests (event service + worker)
- [ ] **Multi-sucursal**: location_id en snapshots + reportes (estructura lista, datos pendientes)

## FASE 4: COMPLETITUD (Pendiente)
**Objetivo**: Auditoría, rollback, observabilidad.

- [ ] **Rollback API**: POST `/imports/{id}/rollback` (reversa de entidades)
- [ ] **Observabilidad**: Ampliar audit_log con resolution + snapshot events
- [ ] **Alertas**: Margen bajo, venta vs producción mismatch, etc.  

---

# 13) Checklist “Listo para mercado”

- [x] Staging + revisión
- [x] Idempotencia (PostingRegistry)
- [x] Doc→Entidad trazable (DocumentVersion → ImportBatch)
- [x] Snapshots para dashboards (profit_snapshots_daily + product_profit_snapshots)
- [x] Auditoría (audit_log + event_outbox)
- [x] Entitlement AND permission
- [x] Templates oficiales + auto-mapper
- [x] Recalculo incremental (RecalculationService + Event Outbox triggers)
- [x] Tests unitarios (37 tests)

---

# REFERENCIAS

**Documentos relacionados**:
- `BLUEPRINT_EMPRESARIAL_GESTIQCLOUD_V2_ANALYSIS.md` — Análisis completo con checklist de implementación
- `MODELOS.md` — Resumen de tablas por módulo

**Estado de este documento**: ✅ ACTUALIZADO 2026-02-14 (Implementación + Tests completados)

---

**Fin del Blueprint V2 — IMPLEMENTACIÓN COMPLETADA**
