# SPEC-1-Importador documental GestiqCloud

## Background

GestiqCloud necesita un módulo de **ingesta y digitalización** que procese documentos heterogéneos (facturas, recibos, extractos/movimientos bancarios, tickets, fotos de documentos, PDF y hojas de cálculo) y los convierta en **datos estructurados normalizados** para su posterior uso contable/financiero. 

El objetivo es cubrir todo el ciclo de vida de la importación:

- **Carga** por lotes o individual (drag & drop, API y conectores externos), con control de versiones, deduplicación e idempotencia.
- **Pre‑proceso** (seguridad y calidad): antivirus, clasificación de tipo de documento, mejora de imagen (deskew, denoise, recorte, corrección de perspectiva), extracción OCR multilenguaje.
- **Extracción** de campos clave (proveedor/cliente, totales, impuestos, líneas, fechas, IBAN, conceptos), y **normalización** a un esquema estándar (p.ej., UBL 2.3/Facturae para facturas; esquema interno para recibos; **ISO 20022 CAMT.053/MT940** para banca).
- **Validación** y reconciliación (reglas fiscales/regionales Ecuador/España, totales vs. líneas, monedas/impuestos), con **revisión humana** cuando sea necesario.
- **Publicación** a los módulos de contabilidad/ERP, con auditoría completa y trazabilidad por inquilino (multi‑tenant), métricas de precisión y re‑proceso.

**Alcance inicial confirmado**: Países **Ecuador y España**. Extracción **self‑hosted** con **Tesseract + reglas/ML** y pipelines propios.

## Requirements

### Must (imprescindibles)
- **Multi‑tenant** estricto (scoping por empresa/tenant en endpoints, queries y storage).
- **Pipelines de importación** por lote: *staging → validation → promotion* con idempotencia y deduplicación por hash (por tipo) tal como ya implementaste en `/imports`.
- **OCR self‑hosted** (Tesseract) con soporte `spa+eng` y diccionarios; mejora de imagen (deskew/denoise) para fotos.
- **Clasificación básica** de documento (factura/recibo/banco/otros) + ruteo a validadores especializados.
- **Normalización canónica**: facturas a UBL/Facturae (o esquema interno equivalente bien versionado); bancos a **CAMT.053/MT940/CSV**; recibos a esquema interno.
- **Validación** de campos, totales/impuestos, fechas y formatos por país (SRI/ES) + motores de reglas parametrizables.
- **Correcciones** con auditoría (ya cuentas con `ImportItemCorrection`) y **revalidación**.
- **Lineage & promoción** con trazabilidad (`ImportLineage`) e idempotencia fuerte.
- **Seguridad**: antivirus (ClamAV), detección de tipo (libmagic), límites de tamaño/páginas, sandbox PDF.
- **Almacenamiento** de archivos en **S3‑compatible** (MinIO) con claves presignadas y retención; encriptación en tránsito y en reposo.
- **Procesamiento asíncrono** con **cola** (Redis/Rabbit) y **workers** (Celery/Dramatiq) + reintentos y DLQ.
- **Observabilidad**: logs estructurados con correlation‑id por batch, métricas (prometheus) y trazas (OpenTelemetry).
- **RBAC** básico por rol (cargar, revisar, promover) y registro de auditoría (WORM) por tenant.
- **API** versionada (`/api/v1/imports`), OpenAPI completa y paginación/filtros en listados.

### Should (debería tener)
- **Verificación de firmas digitales**:
  - **Ecuador (SRI)**: validar **XAdES** en XML de comprobantes y **clave de acceso**; consulta de validez cuando aplique.
  - **España (Facturae)**: validar **XAdES** y metadatos (FACe/FACeB2B).
- **Soporte bancario avanzado**: importadores para **CAMT.053**, **MT940**, CSV/Excel mapeables; conciliación básica.
- **UI de mapeo** (builder) para `ImportMapping`/`transforms` con pruebas rápidas y clonación por versión.
- **Clasificador** de tipo de documento (ligero) entrenable con feedback de correcciones (active learning).
- **Webhooks / SSE** para progreso de lotes y eventos (ingest/validate/promote/error).
- **Catálogo de errores** con códigos estables y exportación.

### Could (podría tener)
- **Fallback híbrido** opcional a OCR/ extracción en cloud para casos difíciles.
- **Detección de duplicados difusos** (fuzzy) más allá del hash exacto.
- **Autocompletado de proveedores** mediante heurísticas/maestros y validación de **RUC/NIF**.
- **Extracción de QR/barcodes** (p.ej., clave de acceso SRI).

### Won’t (por ahora)
- Emisión/envío oficial de e‑facturas (FACe/SRI).  
- Entrenamiento pesado de LLM/LayoutLM en on‑prem.


## Method

### Visión general (orientado a *digitalización genérica* → tablas destino)

El módulo se estructura como **pipeline genérico** que transforma *cualquier documento* en un **modelo canónico** y, con una propuesta de enrutamiento, lo **publica** en las tablas finales (gasto/ingreso/mov. bancario), manteniendo trazabilidad.

```plantuml
@startuml
skinparam componentStyle rectangle
title GestiqCloud Importador – Componentes (visión general)

package "Imports Service (API)" {
  [Router /api/v1/imports]
  [Mappings CRUD]
  [Preview/Correcciones]
}

package "Workers" {
  [Antivirus/Preprocess]
  [OCR (Tesseract)]
  [Classifier]
  [Extractor]
  [Validator EC/ES]
  [Router/Publisher]
  [Thumbnailer]
}

[MinIO/S3] -down-> [Router /api/v1/imports]
[PostgreSQL] -down-> [Router /api/v1/imports]
[Redis/Queue] <-down-> [Workers]
[ClamAV] <-left- [Antivirus/Preprocess]
[OpenTelemetry] <- [Workers]
[ERP/Contabilidad] <- [Router/Publisher]
@enduml
```

#### Flujo principal

```plantuml
@startuml
actor User
User -> API: POST /batches
API -> S3: presigned upload (file_key)
User -> API: POST /batches/{id}/ingest (file_key|rows)
API -> Queue: enqueue(preprocess+ocr)

Queue -> "OCR (Tesseract)": scan AV, enhance, OCR
"OCR (Tesseract)" -> Queue: enqueue(classify)
Queue -> Classifier: infer doc_type
Classifier -> Queue: enqueue(extract)
Queue -> Extractor: campos -> normalized JSON
Extractor -> Validator: reglas EC/ES + totales
Validator -> DB: status VALIDATED_OK/FAIL
User -> API: PATCH item (correcciones)
API -> Validator: revalidate
User -> API: POST /batches/{id}/promote
API -> Publisher: upsert tablas destino (gasto/ingreso/banco)
Publisher -> DB: lineage + idempotencia
@enduml
```

#### Estados del ítem

```plantuml
@startuml
[*] --> NEW
NEW --> INGESTED
INGESTED --> SCANNED
SCANNED --> OCR_DONE
OCR_DONE --> CLASSIFIED
CLASSIFIED --> EXTRACTED
EXTRACTED --> VALIDATED_OK
EXTRACTED --> VALIDATED_FAIL
VALIDATED_OK --> READY_TO_PROMOTE
READY_TO_PROMOTE --> PROMOTED
VALIDATED_FAIL --> CORRECTING
CORRECTING --> EXTRACTED
PROMOTED --> [*]
@enduml
```

### Modelo canónico (JSON) – resumen

> Objetivo: **unificar** todos los formatos (foto/PDF/Excel/CSV/MT940/CAMT/Facturae/UBL) a un **schema estable** en `import_items.normalized` que facilite el enrutamiento.

```json
{
  "doc_type": "expense_receipt|invoice|bank_tx|other",
  "country": "EC|ES",
  "currency": "USD|EUR",
  "issue_date": "YYYY-MM-DD",
  "vendor": { "name": "", "tax_id": "", "country": "" },
  "buyer":  { "name": "", "tax_id": "" },
  "totals": { 
    "subtotal": 0.0, "tax": 0.0, "total": 0.0,
    "tax_breakdown": [{ "rate": 12, "amount": 1.20, "code": "IVA12-EC" }]
  },
  "lines": [{ "desc": "", "qty": 1, "unit_price": 0.0, "total": 0.0, "tax_code": "" }],
  "payment": { "method": "cash|card|transfer", "iban": "", "card_last4": "" },
  "bank_tx": { "amount": 0.0, "direction": "debit|credit", "value_date": "", "narrative": "" },
  "routing_proposal": { "target": "expenses|income|bank_movements", "category_code": "FUEL", "account": "6290", "confidence": 0.86 },
  "attachments": [{ "file_key": "s3://…", "mime": "application/pdf", "type": "original" }]
}
```

- **doc_type** es el resultado del clasificador (recibo/factura/banco).
- **routing_proposal** es la **sugerencia** (no obligatoria) para publicar.

### Enrutamiento a tablas destino (publish)

Al promover (`POST /batches/{id}/promote`) se mapea el canónico a las tablas finales. Propuesta mínima:

**Tabla `expenses`**  
`(id uuid, empresa_id uuid, vendor_id uuid null, issue_date date, currency text, subtotal numeric, tax_total numeric, total numeric, category_code text null, account text null, source_item_id uuid unique, created_at timestamptz)`

**Tabla `expense_lines`**  
`(id uuid, expense_id uuid fk, description text, qty numeric, unit_price numeric, tax_code text, tax_amount numeric, total numeric)`

**Tabla `incomes`** *(análoga a expenses)* y `income_lines`.

**Tabla `bank_movements`**  
`(id uuid, empresa_id uuid, value_date date, amount numeric, currency text, direction text, narrative text, external_ref text null, source_item_id uuid unique, created_at timestamptz)`

**Tabla `attachments`**  
`(id uuid, owner_type text, owner_id uuid, file_key text, mime text, pages int, created_at timestamptz)`

**Tabla `vendors`** *(catálogo opcional)*  
`(id uuid, empresa_id uuid, name text, tax_id text, country text)` con índice único por `(empresa_id, tax_id)` cuando aplique.

**Idempotencia**: `source_item_id` único en tablas destino + `dedupe_hash` en `import_items`.

### Endpoints complementarios (mínimos para el flujo genérico)

- `GET /batches/{id}/items/{itemId}/proposal` → devuelve `routing_proposal` y el **diff** hacia la tabla destino.
- `POST /batches/{id}/items/{itemId}/route` → confirma/override `{ target, category_code, account, vendor_id? }` y marca **READY_TO_PROMOTE**.
- `POST /batches/{id}/promote` ya existente → publica todos los **READY_TO_PROMOTE**.

### Validación y deduplicación

- **Validador por país/tipo** (plug‑in): verifica fechas, monedas, totales, `tax_id` (formato RUC/NIF), tasas de IVA/ICE, etc. Reporta un **catálogo de errores** estable.
- **Deduplicación**: `dedupe_hash = SHA256(empresa_id|doc_type|issue_date|currency|vendor_tax_id|total)` para facturas/recibos; para banca usar `value_date|amount|currency|narrative_norm`.

### Notas de implementación

- Correcciones (`PATCH …/items/{itemId}`) actualizan `normalized`, recalculan validación y **re‑generan `routing_proposal`**.
- OCR fotos: OpenCV (deskew/denoise/threshold) → Tesseract (`spa+eng`, `--psm 4/6/11`, whitelist parcial para importes/fechas).
- Extractor: parsers específicos (Facturae/UBL/XML, PDF text, OCR text, CSV/Excel, CAMT/MT940) que **siempre** emiten el JSON canónico.

## Implementation

### Operación y despliegue sin Docker (Perfil A)

> Mantener **producción sin Docker** es totalmente válido. Recomendación: **prod = bare‑metal/VM con systemd**; **dev/QA = Docker Compose** para paridad.

**Paquetes del sistema (Ubuntu/Debian)**
```bash
sudo apt-get update && sudo apt-get install -y \
  tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng libtesseract-dev \
  libzbar0 libmagic1 clamav-daemon redis-server \
  python3-venv build-essential
```

**Estructura**
```
/srv/gestiq/            # código app
/srv/gestiq/venv/       # venv python
/etc/gestiq/gestiq.env  # variables de entorno
/run/gestiq-api.sock    # socket gunicorn
/var/log/gestiq/        # logs app
```

**/etc/gestiq/gestiq.env (ejemplo)**
```
# DB / Redis
DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/gestiq
REDIS_URL=redis://127.0.0.1:6379/1
# OCR tuning (2 CPU)
IMPORTS_OCR_DPI=200
IMPORTS_OCR_LANG=spa+eng
IMPORTS_OCR_PSM=6
IMPORTS_OCR_WORKERS=2
IMPORTS_MAX_PAGES=20
OMP_THREAD_LIMIT=1
# RLS tenant (lo fija el middleware por request)
```

**API FastAPI (gunicorn + uvicorn workers) — /etc/systemd/system/gestiq-api.service**
```ini
[Unit]
Description=GestiqCloud API
After=network.target redis-server.service clamav-daemon.service

[Service]
Type=simple
EnvironmentFile=/etc/gestiq/gestiq.env
WorkingDirectory=/srv/gestiq
ExecStart=/srv/gestiq/venv/bin/gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind unix:/run/gestiq-api.sock \
  --workers 2 --timeout 120 --access-logfile - --error-logfile -
User=www-data
Group=www-data
RuntimeDirectory=gestiq-api
Restart=always

[Install]
WantedBy=multi-user.target
```

**Worker de importación – opción 1 (tu runner actual) — /etc/systemd/system/gestiq-runner.service**
```ini
[Unit]
Description=Gestiq Imports OCR Job Runner
After=network.target redis-server.service

[Service]
Type=simple
EnvironmentFile=/etc/gestiq/gestiq.env
WorkingDirectory=/srv/gestiq
ExecStart=/srv/gestiq/venv/bin/python -m app.modules.imports.application.job_runner_main
User=www-data
Group=www-data
Restart=always

[Install]
WantedBy=multi-user.target
```
*(Implementa `job_runner_main.py` que arranque `job_runner.start()` y gestione señales.)*

**Worker de importación – opción 2 (Celery sin Docker) — /etc/systemd/system/gestiq-worker.service**
```ini
[Unit]
Description=Gestiq Imports Celery Worker
After=network.target redis-server.service

[Service]
Type=simple
EnvironmentFile=/etc/gestiq/gestiq.env
WorkingDirectory=/srv/gestiq
ExecStart=/srv/gestiq/venv/bin/celery -A app.modules.imports.application.celery_app.celery \
  worker --loglevel=INFO --concurrency=2 \
  -Q imports_pre,imports_ocr,imports_ml,imports_etl,imports_val,imports_route,imports_pub
User=www-data
Group=www-data
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx (proxy a socket) — /etc/nginx/sites-available/gestiq**
```nginx
upstream gestiq_api { server unix:/run/gestiq-api.sock fail_timeout=0; }
server {
  listen 80; server_name _;
  client_max_body_size 16m;  # subidas
  location / {
    proxy_pass http://gestiq_api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 120s;
  }
}
```

**ClamAV**
```bash
sudo systemctl enable clamav-freshclam --now
sudo systemctl enable clamav-daemon --now
```

**Puesta en marcha**
```bash
python3 -m venv /srv/gestiq/venv
source /srv/gestiq/venv/bin/activate
pip install -r requirements.txt
sudo systemctl daemon-reload
sudo systemctl enable --now gestiq-api.service gestiq-runner.service  # o gestiq-worker.service
sudo systemctl status gestiq-api.service
```

**Concurrencias recomendadas (2 CPU)**
- Gunicorn `--workers 2`.
- Celery/runner: 2 procesos OCR; fija `IMPORTS_OCR_WORKERS=2` y `OMP_THREAD_LIMIT=1`.
- Redis local, sólo loopback y con `requirepass` si hay multi‑usuario.


### A. Multi‑tenant canónico con `tenant_id` (sin tocar PK de `core_empresa`)

**Objetivo:** Mantener `core_empresa.id` (**INT**) durante 1–2 releases y migrar todo el *staging de importación* a **`tenant_id` (UUID)**, alineado con `public.tenants(id)` y **RLS fuerte**. `empresa_id` queda en paralelo (compatibilidad) hasta retirarlo.

#### A.1 Alembic – añadir `tenant_id` y backfill

> Asumo que existe `core_empresa.tenant_id UUID` → FK a `public.tenants(id)`. Si no, crear tabla de mapeo `empresa_tenant_map(old_empresa_id INT, tenant_id UUID)`.

```python
# alembic revision -m "imports: add tenant_id + indexes"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

UUID = postgresql.UUID(as_uuid=True)

TABLES = [
  'import_batches','import_items','import_mappings',
  'import_item_corrections','import_lineage','import_attachments',
  'import_ocr_jobs','auditoria_importacion'
]

def upgrade():
    for t in TABLES:
        op.add_column(t, sa.Column('tenant_id', UUID, nullable=True))
    # Backfill usando core_empresa.tenant_id
    op.execute('''
      UPDATE import_batches b
      SET tenant_id = e.tenant_id
      FROM core_empresa e
      WHERE b.empresa_id = e.id;
      UPDATE import_items i SET tenant_id = b.tenant_id FROM import_batches b WHERE i.batch_id=b.id;
      UPDATE import_mappings m SET tenant_id = e.tenant_id FROM core_empresa e WHERE m.empresa_id=e.id;
      UPDATE import_item_corrections c SET tenant_id = e.tenant_id FROM core_empresa e WHERE c.empresa_id=e.id;
      UPDATE import_lineage l SET tenant_id = e.tenant_id FROM core_empresa e WHERE l.empresa_id=e.id;
      UPDATE import_attachments a SET tenant_id = i.tenant_id FROM import_items i WHERE a.item_id=i.id;
      UPDATE import_ocr_jobs j SET tenant_id = e.tenant_id FROM core_empresa e WHERE j.empresa_id=e.id;
      UPDATE auditoria_importacion a SET tenant_id = e.tenant_id FROM core_empresa e WHERE a.empresa_id=e.id;
    ''')
    # NOT NULL + FK
    for t in TABLES:
        op.alter_column(t, 'tenant_id', nullable=False)
        op.create_foreign_key(f"fk_{t}_tenant", t, 'tenants', ['tenant_id'], ['id'], source_schema=None, referent_schema='public')
    # Índices y unicidades por tenant
    op.create_index('ix_batches_tenant_status_created','import_batches',['tenant_id','status','created_at'])
    op.create_index('ix_items_tenant_dedupe','import_items',['tenant_id','dedupe_hash'])
    op.create_unique_constraint('uq_items_tenant_idem','import_items',['tenant_id','idempotency_key'])
    op.create_index('ix_items_tenant_norm_gin','import_items',['normalized'], postgresql_using='gin')
    op.create_index('ix_items_tenant_doc_type','import_items',[sa.text("(normalized->>'doc_type')")], postgresql_where=sa.text("normalized ? 'doc_type'"))

    # Opcional: marcar empresa_id como deprecated (no null aún)


def downgrade():
    raise NotImplementedError
```

#### A.2 Modelos (SQLAlchemy) – añadir `tenant_id`
```python
from sqlalchemy.dialects.postgresql import UUID as PGUUID
UUID = PGUUID(as_uuid=True)

class ImportBatch(Base):
    tenant_id = mapped_column(UUID, ForeignKey('public.tenants.id'), index=True, nullable=False)
    empresa_id = mapped_column(ForeignKey('core_empresa.id'), index=True, nullable=False)  # deprecado futuro

class ImportItem(Base):
    tenant_id = mapped_column(UUID, ForeignKey('public.tenants.id'), index=True, nullable=False)
    # mantener campos actuales
    __table_args__ = (
        UniqueConstraint('tenant_id','idempotency_key', name='uq_items_tenant_idem'),
        Index('ix_items_tenant_dedupe','tenant_id','dedupe_hash'),
    )
```

#### A.3 RLS (Row‑Level Security) en PostgreSQL

- Estrategia: fijar al abrir la sesión DB `SET app.tenant_id = '<uuid>'` y usar el helper `tenant_id_sql_expr()` (ver `app/db/rls.py`) en políticas/consultas en lugar de referenciar `current_setting` directamente.

```sql
ALTER TABLE import_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY p_import_items_tenant ON import_items
  USING (tenant_id = tenant_id_sql_expr())
  WITH CHECK (tenant_id = tenant_id_sql_expr());

-- Repetir para import_batches, import_mappings, import_item_corrections, import_lineage, import_attachments,
-- import_ocr_jobs, auditoria_importacion y las tablas destino (expenses, incomes, bank_movements, attachments).
```

**Hook en FastAPI/SQLAlchemy** (por request):
```python
from sqlalchemy import text

def set_tenant(session, tenant_id: str):
    session.execute(text("SET app.tenant_id = :t"), {"t": tenant_id})
```

#### A.4 API y validación de contexto tenant

- El **tenant** se obtiene del token/JWT o del subdominio; **nunca** del body.  
- Middlewares: resolver `tenant_id` y setearlo en la sesión DB (ver *hook*).  
- Todos los endpoints existentes de `/api/v1/imports` operan bajo RLS sin cambios de firma.

### B. Hardening JSONB, estados y catálogos

- Convertir `raw/normalized/errors` y `mappings/transforms/defaults` a **JSONB** con índices **GIN** (ya incluido).  
- **Enums/Checks** para estados (`batches`, `items`, `ocr_jobs`).  
- **Catálogo de errores** y objetos `{code, field, params}` en `errors`.

### C. Decisiones de enrutamiento & publicación

- `import_routing_decisions` (proposed/confirmed/overridden) **scoped por `tenant_id`**.  
- `Publisher` hace **upsert** a `expenses/incomes/bank_movements` con `source_item_id` y `tenant_id`.

### D. Rastro y auditoría

- Aprovechar tu `auditoria_importacion` (añadido `tenant_id`) para loguear **diffs** y decisiones; enlazar `batch_id/item_id`.

### E. Seguridad & Observabilidad

- ClamAV, libmagic; límites por tamaño y páginas; enmascarado de PAN.  
- Logs JSON con `tenant_id` + métricas Prometheus y trazas OTel.

## Milestones

**T0 – Tenantización canónica**  
- Añadir `tenant_id UUID` a todas las tablas `import_*` y `auditoria_importacion`; backfill desde `core_empresa.tenant_id` (o tabla mapa).  
- Índices y unicidades `UNIQUE(tenant_id, idempotency_key)` y `INDEX(tenant_id, dedupe_hash)`.

**T1 – RLS fuerte**  
- Activar RLS en todas las tablas `import_*` y destino.  
- Middleware para `SET app.tenant_id` por request; tests de aislamiento de filas.

**T2 – JSONB + estados**  
- Migrar JSON→JSONB, GIN, enums/checks.  
- Catálogo de errores + export estable.

**T3 – Pipeline OCR/extracción**  
- OpenCV/Tesseract; parsers PDF/Facturae/UBL/CSV/Excel/CAMT/MT940; métricas de calidad.

**T4 – Propuestas de enrutamiento**  
- Tabla `import_routing_decisions`, endpoints `/proposal` y `/route`, UI de confirmación.

**T5 – Publicación**  
- Upsert a `expenses/incomes/bank_movements` con `tenant_id` + `source_item_id`; lineage.

**T6 – Deprecación limpia**  
- Retirar `empresa_id` de tablas `import_*` y `auditoria_importacion` tras 1–2 releases; mantener VIEW si se requiere compatibilidad temporal.

**T7 – Observabilidad & Seguridad**  
- Métricas Prometheus/OTel, eventos SSE; DLP básico, retención, WORM lógico.

**T8 – QA/Fixtures**  
- Golden tests con docs reales anonimizados; benchmarks de latencia/throughput por etapa.


## Prompt Pack – “copia/pega” para mantener el módulo PRO, rápido y estable

> Usa estos prompts en tu editor/IA (Copilot/ChatGPT) cuando edites el repo. Cada uno produce código/diffs listos y verifica calidad sin que tengas que recordar detalles.

### 1) PR Review (Arquitectura + Seguridad + Performance)

**Prompt:**
> Actúa como revisor senior de backend para el módulo `apps/backend/app/modules/imports`. Revisa los cambios con foco en: (1) RLS por `tenant_id` en todas las consultas, (2) idempotencia (`idempotency_key` y `dedupe_hash` por tenant), (3) JSON→JSONB + índices GIN, (4) estados tipados/validados, (5) OCR rápido (skip PDF nativo, 200 DPI GRAY, multiproceso, caché), (6) seguridad de archivos (size/pages, libmagic, ClamAV si disponible), (7) trazabilidad (lineage, auditoría) y (8) métricas/trazas (Prometheus/OTel). Señala problemas con ejemplos de parche (diff unificado) y añade una lista de *action items* bloqueantes y no bloqueantes.

### 2) Generar migración Alembic (tenantización + JSONB + índices)

**Prompt:**
> Genera una migración Alembic para `apps/backend` que: (a) añada `tenant_id UUID NOT NULL` a las tablas `import_batches, import_items, import_mappings, import_item_corrections, import_lineage, import_attachments, import_ocr_jobs, auditoria_importacion` con FK a `public.tenants(id)` y backfill desde `core_empresa.tenant_id`; (b) convierta `raw, normalized, errors, mappings, transforms, defaults` a JSONB; (c) cree `UNIQUE(tenant_id, idempotency_key)` en `import_items`; (d) índices: `INDEX(tenant_id, dedupe_hash)`, `GIN(normalized)`, parcial `BTREE((normalized->>'doc_type'))`. Devuelve archivo de migración completo y reversible, con guardas para SQLite en tests.

### 3) Políticas RLS por tabla (verificación + tests)

**Prompt:**
> Escribe SQL idempotente para habilitar RLS y crear políticas `USING`/`WITH CHECK` por `tenant_id` en todas las tablas `import_*` y `auditoria_importacion`. Incluye helper de FastAPI/SQLAlchemy para `SET app.tenant_id = :uuid` por request y tests de integración que demuestren aislamiento: el tenant A no ve datos del B, con *fixtures* y *factories*.

### 4) Hook runner inline con advisory lock (Render)

**Prompt:**
> Genera el parche (diff unificado) para `app/main.py` que inicie/detenga el runner `job_runner.start()`/`stop()` en eventos `startup/shutdown` sólo si `IMPORTS_ENABLED=1` y `IMPORTS_RUNNER_MODE=inline`, tomando el liderazgo con `SELECT pg_try_advisory_lock(:key)` y liberándolo en shutdown. Usa `IMPORTS_RUNNER_LOCK` como clave.

### 5) Optimización OCR (photo_utils)

**Prompt:**
> Entrega el **diff unificado** contra `apps/backend/app/modules/imports/application/photo_utils.py` para: (1) detectar texto en PDFs (PyMuPDF) y saltar OCR, (2) render en GRAY a 200 DPI, (3) multiproceso por página con `ProcessPoolExecutor` y caché por SHA‑256, (4) lectura de QR previa (pyzbar), (5) fallback a EasyOCR cuando Tesseract no esté disponible, (6) variables de entorno: `IMPORTS_OCR_*`, `OMP_THREAD_LIMIT`. Mantén firmas públicas.

### 6) Endpoints de propuesta/route + tabla `import_routing_decisions`

**Prompt:**
> Genera la tabla `import_routing_decisions` (proposed/confirmed/overridden, `confidence`), repositorio y endpoints FastAPI: `GET /api/v1/imports/batches/{id}/items/{itemId}/proposal` y `POST /route` que guardan decisión y marcan `READY_TO_PROMOTE`. Incluye validación de `tenant_id` por RLS, esquemas Pydantic y tests de integración.

### 7) Publisher idempotente a dominios (expenses/incomes/bank_movements)

**Prompt:**
> Implementa un `Publisher` con upserts idempotentes en `expenses, expense_lines, incomes, income_lines, bank_movements` usando `tenant_id` y `source_item_id`=`import_items.id`. Registra `import_lineage`. Devuelve repos, servicios y pruebas con *fixtures*.

### 8) Seguridad de archivos (sin Docker)

**Prompt:**
> Añade *guards* previos a OCR/parseo: tamaño máximo, páginas máximas en PDF, `libmagic` para MIME, rechazo de PDFs con JS incrustado si política lo exige, y ruta de *sandbox*. Proporciona código Python y pruebas. Si ClamAV no está presente, simula `clamd` con bandera de entorno para tests.

### 9) Observabilidad (Prometheus + OTel)

**Prompt:**
> Instrumenta el pipeline con métricas (`imports_ingested_total`, `imports_validated_ok_total`, histogramas de latencia por etapa) y trazas OTel con `trace_id=batch_id:item_id`. Entrega el código, *exporters* configurables por env y un dashboard Prometheus mínimo (YAML/JSON) con paneles de P50/P95.

### 10) Tests “golden” y benchmark

**Prompt:**
> Crea *golden tests* para extracción y validación con PDFs/fotos anonimizados (gasolina, peajes, restaurante, parking). Incluye un *benchmark* `bench_ocr.py` que reporte ms por documento y guarde resultados en `/tmp/bench.json`. Establece umbrales: P95 < 5s en 2 CPU.

### 11) Linters y CI (sin Docker)

**Prompt:**
> Añade `ruff`, `black`, `mypy` y un workflow de GitHub Actions que ejecute: lint, type‑check, tests (SQLite) y migra/alembic `--sql` (dry‑run). Falla si la cobertura baja de 80% en `app/modules/imports/**`.

### 12) Checklist de “Definition of Done”

**Prompt:**
> Verifica que el módulo de imports cumple: RLS por tenant, JSONB+GIN, idempotencia por tenant, OCR optimizado, validadores EC/ES, propuestas de enrutamiento, publisher idempotente, lineage, catálogo de errores, métricas/trazas, P95 < 5s (2 CPU), *golden tests* verdes. Entrega reporte marcando ✅/❌ con enlaces a commits.

---

### Snippets rápidos de entorno (Render)
- `IMPORTS_ENABLED=1`, `IMPORTS_RUNNER_MODE=inline`, `IMPORTS_RUNNER_LOCK=8102025`  
- `IMPORTS_OCR_DPI=200`, `IMPORTS_OCR_LANG=spa+eng`, `IMPORTS_OCR_PSM=6`, `IMPORTS_OCR_WORKERS=2`, `IMPORTS_MAX_PAGES=20`, `OMP_THREAD_LIMIT=1`  
- Parche OCR: usa los archivos adjuntos `photo_utils.patch`/`photo_utils_optimized.py` que te dejé.

### Guía de uso
1) Antes de tocar nada, pega el **Prompt 1** en tu PR → tendrás un review automatizado y guía de cambios.  
2) Si falta alguna pieza, pega el prompt correspondiente (2–11) y aplica el diff que te devuelva.  
3) Ejecuta el **Prompt 12** antes de cerrar el PR para validar que cumpliste el DoD.
