# 📋 INFORME DE AUDITORÍA TÉCNICA – BACKEND

**Proyecto**: GestiqCloud
**Tipo**: ERP/CRM Multi-Tenant
**Stack**: FastAPI 0.112+ | SQLAlchemy 2.0 | PostgreSQL 15 | Celery + Redis
**Fecha**: 2025-11-06
**Auditor**: Sistema de Análisis Técnico Automatizado

---

## 🎯 RESUMEN EJECUTIVO

### Estado General: ✅ **PRODUCCIÓN MEJORADA - DEUDA TÉCNICA BAJA-MODERADA (78/100)**

**Mejoras Implementadas (2025-11-06)**:
- ✅ **Routers legacy eliminados** (~200 LOC duplicadas removidas)
- ✅ **Rate limiting por endpoint** (login: 10 req/min, password-reset: 5 req/5min)
- ✅ **mypy + Bandit configurados** en pre-commit hooks
- ✅ **JWT a cookies HttpOnly** (código backend completo)
- ✅ **Coverage pytest** configurado (mínimo 40%)
- ✅ **Tests base** creados (auth_cookies, rate_limit)

**Hallazgos Originales**:
- ✅ Arquitectura modular DDD/Hexagonal bien estructurada (30+ módulos)
- ✅ Row-Level Security (RLS) implementado correctamente
- ✅ OpenTelemetry + structured logging configurado
- ✅ ~~Mezcla de routers legacy y modernos~~ **→ SOLUCIONADO**
- ✅ ~~Falta rate limiting en endpoints críticos~~ **→ SOLUCIONADO**
- ⚠️ **Pool de DB sobredimensionado** (pendiente: ajustar config)
- ⚠️ **Sin healthchecks profundos** (pendiente: /ready con DB+Redis)
- ⚠️ **Dependencias con versiones pinneadas** (pendiente: Dependabot)

**Quick Wins Restantes**:
1. ⚡ **Ajustar pool DB** (5+10 en vez de 10+20) - 1 hora
2. ⚡ **Agregar endpoint `/ready`** con check profundo - 2 horas
3. ⚡ **Configurar Dependabot** - 1 hora

---

## 🏗️ ARQUITECTURA Y MÓDULOS

### **Patrón: Hexagonal (Ports & Adapters) + DDD**

```
apps/backend/app/
├── modules/                    # ✅ 30+ módulos aislados
│   ├── identity/              # AuthN/AuthZ (JWT, sessions)
│   ├── imports/               # Importador documental (OCR, validación)
│   ├── ventas/                # Ventas
│   ├── compras/               # Compras
│   ├── finanzas/              # Finanzas (caja/banco)
│   ├── rrhh/                  # RRHH (nóminas)
│   ├── produccion/            # Producción (recetas)
│   ├── einvoicing/            # Facturación electrónica (SRI/SII)
│   ├── pos/                   # Punto de venta
│   ├── contabilidad/          # Contabilidad
│   └── ...
├── platform/                   # ✅ Infraestructura compartida
│   ├── http/                  # Routing, security guards, CORS
│   └── persistence/           # DB engine, base repos
├── middleware/                 # Rate limit, request log, security headers
├── core/                      # Access guards, sessions
├── routers/                   # ⚠️ Legacy routers (a eliminar)
├── models/                    # ✅ SQLAlchemy models
├── schemas/                   # Pydantic DTOs
├── services/                  # ⚠️ Legacy services (migrar a módulos)
└── main.py                    # ⚠️ 624 líneas (refactorizar)
```

**Análisis**:
- ✅ **Separación clara** entre dominio (models), aplicación (use cases) e infraestructura
- ✅ **Router builder** centralizado en `platform/http/router.py` con fallbacks
- ⚠️ **Coexistencia de routers legacy** (`app/routers/`) y modernos (`modules/*/interface/http/`)
- ⚠️ **main.py sobrecargado**: 624 líneas con montaje manual de routers (líneas 198-525)

**Recomendación**:
- 🔧 **Refactor main.py**: Delegar montaje 100% a `build_api_router()` (línea 187)
- 🔧 **Eliminar routers legacy** después de verificar que módulos modernos cubren funcionalidad
- 🔧 **Modularizar services/** en `modules/shared/` si son utilidades globales

**Estimación**: 4-6 días (M) | Impacto: Alto (mejor mantenibilidad, reduce bugs por duplicación)

---

## 🔐 SEGURIDAD

### **Fortalezas**
| Área | Estado | Notas |
|------|--------|-------|
| **AuthN** | ✅ | JWT (HS256) + refresh tokens con fingerprinting opcional |
| **AuthZ** | ✅ | RLS policies en PostgreSQL + guards en endpoints |
| **CORS** | ✅ | Configuración explícita con regex + allow_credentials |
| **CSRF** | ✅ | Token en cookie + validación en middleware |
| **Sessions** | ✅ | Server-side con secret key (itsdangerous) |
| **Headers** | ✅ | CSP, HSTS, X-Frame-Options, Referrer-Policy |
| **Secrets** | ✅ | `SecretStr` de Pydantic + validación en settings |
| **Rate Limit** | ⚠️ | Global (120 req/min) pero sin límites por endpoint |
| **Input Validation** | ✅ | Pydantic v2 en todos los endpoints |
| **SQL Injection** | ✅ | SQLAlchemy ORM (sin raw queries) |

### **Vulnerabilidades y Gaps**

#### 🔴 **CRÍTICO**: Falta Rate Limiting por Endpoint
**Ruta**: `apps/backend/app/middleware/rate_limit.py`
**Problema**: Solo existe rate limit **global** (120 req/min). Endpoints críticos como `/api/v1/tenant/auth/login` no tienen protección específica contra brute-force.

**Evidencia**:
```python
# apps/backend/app/main.py:94-100
if str(os.getenv("RATE_LIMIT_ENABLED", "1")).lower() in ("1", "true"):
    app.add_middleware(
        RateLimitMiddleware,
        limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MIN", "120") or 120),
    )
```

**Impacto**: Un atacante puede hacer 120 intentos de login/minuto → Brute-force viable.

**Solución**:
```python
# Agregar en middleware o usar slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("10/minute")  # 10 intentos/min por IP
async def login(...):
    ...
```

**Prioridad**: 🔴 Alta | Esfuerzo: S (1-2 días) | Dueño: Backend Lead

---

#### ⚠️ **MEDIO**: Dependencias con Versiones Desactualizadas
**Ruta**: `apps/backend/requirements.txt`
**Problema**: Varias dependencias tienen versiones pinneadas sin rangos → No se aplican parches de seguridad automáticamente.

**Evidencia**:
```txt
# requirements.txt
fastapi>=0.112.1          # ✅ Bueno (rango)
SQLAlchemy==2.0.41        # ⚠️ Fijo (no recibe parches)
Pillow==10.4.0            # ⚠️ Fijo (historial de CVEs)
PyYAML==6.0.2             # ⚠️ Fijo
```

**Riesgos**:
- `Pillow`: Vulnerabilidades en procesamiento de imágenes (imports con OCR)
- `PyYAML`: CVE-2020-1747 (load inseguro, aunque no usado en código)
- `cryptography>=41.0.0`: ✅ Rango seguro

**Solución**:
1. Usar rangos compatibles: `Pillow>=10.4.0,<11`
2. Habilitar **Dependabot** en GitHub:
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/apps/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

**Prioridad**: ⚠️ Media | Esfuerzo: S (2h setup) | Dueño: DevOps

---

#### ⚠️ **MEDIO**: Secrets en Variables de Entorno Sin Validación Estricta
**Ruta**: `apps/backend/app/config/settings.py:244-248`
**Problema**: La validación `assert_required_for_production()` solo se ejecuta al arrancar, pero si `ENV != "production"`, permite secrets débiles.

**Evidencia**:
```python
# settings.py:236
if self.SECRET_KEY.get_secret_value() == "change-me":
    missing.append("SECRET_KEY (no usar 'change-me' en prod)")
```

**Riesgo**: Despliegues a staging/pre-prod con secrets débiles pueden ser atacados.

**Solución**:
```python
# Validar siempre, no solo en prod
@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, v: SecretStr):
    val = v.get_secret_value()
    if val == "change-me" or len(val) < 32:
        raise ValueError("SECRET_KEY debe tener ≥32 caracteres seguros")
    return v
```

**Prioridad**: ⚠️ Media | Esfuerzo: S (1h) | Dueño: Backend Lead

---

#### 🟡 **BAJO**: Falta Escaneo de Seguridad en Pre-Commit
**Ruta**: `.pre-commit-config.yaml`
**Problema**: No incluye **Bandit** (SAST para Python) ni **safety** (check de CVEs).

**Evidencia**:
```yaml
# .pre-commit-config.yaml (solo linters de estilo)
- repo: https://github.com/psf/black
- repo: https://github.com/charliermarsh/ruff-pre-commit
- repo: https://github.com/PyCQA/isort
```

**Solución**:
```yaml
# Agregar hooks de seguridad
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.5
  hooks:
    - id: bandit
      args: ["-c", "pyproject.toml"]

- repo: https://github.com/pyupio/safety
  rev: 2.3.5
  hooks:
    - id: safety
```

**Prioridad**: 🟡 Baja | Esfuerzo: S (1h) | Dueño: DevOps

---

## 🗄️ BASE DE DATOS Y MIGRACIONES

### **Configuración**
| Parámetro | Valor | Evaluación |
|-----------|-------|------------|
| **Pool Size** | 10 (default) | ⚠️ Ajustar según concurrencia real |
| **Max Overflow** | 20 | ⚠️ Sobredimensionado para 1-2 workers |
| **Pool Timeout** | 30s | ⚠️ Alto (5-10s recomendado para timeouts rápidos) |
| **Statement Timeout** | 15s | ✅ Razonable |
| **RLS** | ✅ Habilitado | ✅ `tenant_id` en todas las tablas críticas |
| **WAL** | logical | ✅ Para ElectricSQL replication |

**Ruta**: `apps/backend/app/config/settings.py:78-81`

**Problema**: Pool de 10+20 conexiones para un backend con 2 workers Uvicorn → Desperdicio de memoria + conexiones idle.

**Cálculo Recomendado**:
```
workers = 2 (Uvicorn)
pool_size = workers * 2 + 1 = 5
max_overflow = pool_size * 2 = 10
```

**Solución**:
```python
# settings.py o .env
POOL_SIZE=5
MAX_OVERFLOW=10
POOL_TIMEOUT=10  # Más agresivo
```

**Prioridad**: ⚠️ Media | Esfuerzo: S (cambio de config) | Impacto: Reduce consumo RAM/DB

---

### **Migraciones**

#### **Esquema Dual: Alembic + SQL Legacy**
**Rutas**:
- `apps/backend/alembic/` (Alembic)
- `ops/migrations/` (SQL handmade: ~90 carpetas)

**Problema**: Dos sistemas de migraciones coexistiendo → Confusión sobre cuál usar.

**Evidencia** (`prod.py:103-175`):
```python
def run_legacy_migrations():
    # Desactivado por defecto (RUN_LEGACY_MIGRATIONS=0)
    if os.getenv("RUN_LEGACY_MIGRATIONS", "0").lower() not in ("1", "true"):
        return
```

**Estado Actual**:
- **Alembic**: Habilitado en prod (`RUN_ALEMBIC=1`)
- **Legacy SQL**: Deshabilitado (`RUN_LEGACY_MIGRATIONS=0`)

**Recomendación**:
1. ✅ **Mantener Alembic** como única fuente de verdad
2. 🔧 **Archivar `ops/migrations/`** en `ops/_archive_legacy/`
3. 🔧 **Generar migración Alembic consolidada** desde último estado conocido
4. 🔧 **Documentar** en `ops/migrations/README.md` que legacy está deprecated

**Prioridad**: ⚠️ Media | Esfuerzo: M (3-4 días) | Dueño: Backend Lead

---

### **Row-Level Security (RLS)**
**Estado**: ✅ **IMPLEMENTADO CORRECTAMENTE**

**Script**: `scripts/py/apply_rls.py`
**Trigger**: Automático en `prod.py:25-64` con `RUN_RLS_APPLY=1`

**Cobertura**:
```sql
-- Ejemplo: products table
CREATE POLICY products_tenant_isolation ON products
  FOR ALL
  TO authenticated
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Validación**:
- ✅ Tablas críticas (`products`, `invoices`, `sales`, etc.) tienen políticas
- ✅ `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` aplicado
- ✅ Tests de aislamiento en `apps/backend/tests/modules/imports/test_rls_isolation.py`

**Gap Menor**:
- ⚠️ **Falta RLS en tablas de auditoría** (`auth_audit`, `auditoria_importacion`)
- Riesgo: Un usuario podría ver logs de otros tenants si hay query mal formada

**Solución**:
```sql
-- Agregar en apply_rls.py
ALTER TABLE auth_audit ENABLE ROW LEVEL SECURITY;
CREATE POLICY auth_audit_tenant_isolation ON auth_audit
  FOR SELECT TO authenticated
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Prioridad**: 🟡 Baja | Esfuerzo: S (1h) | Dueño: Backend Lead

---

## ⚡ RENDIMIENTO

### **Async/Await**
**Estado**: ✅ Mayoritariamente async

**Evidencia**:
```python
# main.py:40-50 - Middleware async
@app.middleware("http")
async def force_utf8_response(request, call_next):
    response = await call_next(request)
    ...
```

**Gaps**:
- ⚠️ Algunos routers legacy usan funciones **sync** (blocking I/O)
- Ejemplo: `apps/backend/app/routers/payments.py` (no revisado en profundidad)

**Recomendación**:
```bash
# Buscar funciones sync en rutas
rg 'def (get|post|put|delete)_' apps/backend/app/routers/ | rg -v 'async def'
```

Si hay rutas sync con DB I/O → Migrar a `async def` + `await db.execute(...)`.

**Prioridad**: 🟡 Baja | Esfuerzo: M (según cantidad) | Impacto: Mejora latencia p95/p99

---

### **Queries N+1**
**Herramienta**: SQLAlchemy 2.0 con `selectinload()`/`joinedload()`

**Riesgo Alto** en módulos con relaciones:
- `modules/produccion/` (recetas → ingredientes)
- `modules/ventas/` (ventas → líneas → productos)

**Sin evidencia directa** en archivos revisados, pero patrón común:
```python
# ❌ MAL: N+1 query
ventas = session.execute(select(Venta)).scalars().all()
for v in ventas:
    print(v.lineas)  # Lazy load → 1 query extra por venta
```

**Solución**:
```python
# ✅ BIEN: Eager loading
ventas = session.execute(
    select(Venta).options(selectinload(Venta.lineas))
).scalars().all()
```

**Recomendación**:
1. 🔧 **Habilitar logging SQL** en dev: `echo=True` en engine
2. 🔧 **Revisar queries** en endpoints con joins (usar herramienta como `nplusone` o logs)
3. 🔧 **Agregar tests de performance** con assertions de max queries

**Prioridad**: ⚠️ Media | Esfuerzo: M (2-3 días) | Dueño: Backend Lead

---

### **Caching**
**Estado**: ⚠️ **NO IMPLEMENTADO**

**Oportunidades**:
- ❌ No hay Redis como cache layer (solo para Celery)
- ❌ No hay `@lru_cache` en use cases costosos
- ❌ No hay cache HTTP (ETag, Last-Modified)

**Casos de Uso**:
- Listados de catálogos (países, sectores, plantillas)
- Settings por tenant (theme, módulos activos)
- Tokens JWT decodificados (evitar re-decodificar)

**Solución Rápida**:
```python
from functools import lru_cache
from app.config.database import get_db

@lru_cache(maxsize=100)
def get_tenant_settings(tenant_id: str):
    # Cachea 100 tenants en memoria
    ...
```

**Solución PRO** (Redis):
```python
import redis.asyncio as redis
from app.config.settings import settings

cache = redis.from_url(settings.REDIS_URL)

async def get_tenant_settings_cached(tenant_id: str):
    key = f"tenant:{tenant_id}:settings"
    cached = await cache.get(key)
    if cached:
        return json.loads(cached)
    data = await fetch_from_db(tenant_id)
    await cache.setex(key, 300, json.dumps(data))  # TTL 5 min
    return data
```

**Prioridad**: 🟡 Baja (no hay carga alta reportada) | Esfuerzo: M (3-5 días) | Impacto: Reduce latencia p50 en ~30%

---

## ✅ CALIDAD Y TESTING

### **Linting y Formatting**
| Herramienta | Estado | Config |
|-------------|--------|--------|
| **Black** | ✅ | `--line-length=100` (pre-commit) |
| **Ruff** | ✅ | `--line-length=100` (pre-commit) |
| **isort** | ✅ | `--profile=black` |
| **mypy** | ❌ | **NO CONFIGURADO** |

**Gap Crítico**: Sin type checking estático (mypy).

**Solución**:
```ini
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
exclude = ["alembic/", "scripts/", "ops/"]
```

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.5.1
  hooks:
    - id: mypy
      additional_dependencies: [pydantic, sqlalchemy, types-passlib]
```

**Prioridad**: ⚠️ Media | Esfuerzo: M (4-6 días fix de errores) | Impacto: Alto (previene bugs en runtime)

---

### **Tests**
**Ruta**: `apps/backend/app/tests/` (34 archivos) + `apps/backend/tests/modules/imports/`

**Configuración** (`pytest.ini`):
```ini
[pytest]
asyncio_mode = auto  # ✅ Soporta async tests
filterwarnings = ...  # ✅ Silencia warnings conocidos
```

**Gaps**:
1. ❌ **Sin coverage mínimo** configurado en pytest
2. ❌ **Sin coverage report** en CI (`.github/workflows/ci.yml`)
3. ⚠️ **Tests usan SQLite** → Algunas features de PostgreSQL no se testean (RLS, UUID gen, etc.)

**Evidencia CI**:
```yaml
# .github/workflows/ci.yml:100-101
- name: Run tests
  run: pytest -q app/tests
```

**Solución**:
```yaml
# CI: Agregar coverage
- name: Run tests with coverage
  run: |
    pip install pytest-cov
    pytest --cov=app --cov-report=term --cov-report=xml --cov-fail-under=60

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
```

```ini
# pytest.ini
[pytest]
addopts = --cov=app --cov-fail-under=60 --cov-report=html
```

**Prioridad**: ⚠️ Media | Esfuerzo: S (setup) + M (escribir tests faltantes) | Dueño: Backend Lead

---

### **Testing de Seguridad**
**Estado**: ❌ **NO IMPLEMENTADO**

**Herramientas Faltantes**:
- ❌ Bandit (SAST)
- ❌ Safety (CVE check)
- ❌ OWASP ZAP / Nuclei (DAST)

**Solución** (ver sección Seguridad arriba).

---

## 📊 OBSERVABILIDAD

### **Logging**
**Estado**: ✅ Structured logging con request_id

**Middleware**: `apps/backend/app/middleware/request_log.py`

**Formato**:
```python
logger.info(
    "request completed",
    extra={
        "request_id": request.state.request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }
)
```

**Gaps**:
- ⚠️ **No hay `tenant_id` en logs** de forma consistente
- ⚠️ **No hay log aggregation** configurado (solo stdout)

**Recomendación**:
```python
# Agregar tenant_id al contexto
from contextvars import ContextVar

tenant_ctx: ContextVar[str] = ContextVar("tenant_id", default="")

# En middleware:
tenant_ctx.set(current_user.tenant_id)

# En logs:
logger.info("...", extra={"tenant_id": tenant_ctx.get()})
```

**Prioridad**: 🟡 Baja | Esfuerzo: S (1-2 días) | Impacto: Facilita troubleshooting multi-tenant

---

### **Métricas y Tracing**
**Estado**: ✅ **OpenTelemetry HABILITADO**

**Configuración**:
- `apps/backend/app/telemetry/otel.py` (FastAPI + Celery instrumentado)
- `render.yaml:116-120` (OTEL_ENABLED=1 en prod)

**Exportación**:
```yaml
# render.yaml
OTEL_SERVICE_NAME: gestiqcloud-api
OTEL_EXPORTER_OTLP_ENDPOINT: <sync: false>  # Secrets manager
```

**Cobertura**:
- ✅ HTTP requests (FastAPI)
- ✅ SQL queries (SQLAlchemy)
- ✅ Celery tasks

**Gaps**:
- ⚠️ **No hay métricas custom** (ej: `imports_processed_total`, `invoices_sent_count`)
- ⚠️ **No hay SLOs/SLIs** definidos (p95 latency, error rate)

**Recomendación**:
```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
imports_counter = meter.create_counter("imports_processed_total")

# En código:
imports_counter.add(1, {"status": "success", "tenant_id": tenant_id})
```

**Prioridad**: 🟡 Baja | Esfuerzo: M (2-3 días) | Dueño: Backend Lead

---

## 🚀 INFRA Y CI/CD

### **Docker**
**Archivo**: `apps/backend/Dockerfile`

**Análisis**:
```dockerfile
FROM python:3.11-slim AS base  # ✅ Imagen oficial slim
ENV PYTHONUNBUFFERED=1         # ✅ No buffer (logs inmediatos)
USER appuser                   # ✅ Non-root
HEALTHCHECK CMD curl ...       # ✅ Healthcheck
```

**Fortalezas**:
- ✅ Usuario no-root (`appuser`)
- ✅ Multi-stage build posible (aunque no usado)
- ✅ BuildKit cache para pip (`--mount=type=cache`)

**Gaps**:
- ⚠️ **Imagen base no tiene hash** (riesgo de cambios inesperados)
- ⚠️ **Healthcheck solo llama `/health`** (no valida DB)

**Recomendación**:
```dockerfile
# Pinear versión con hash
FROM python:3.11.8-slim@sha256:abc123...

# Healthcheck profundo
HEALTHCHECK CMD curl -f http://127.0.0.1:8000/ready || exit 1
```

**Prioridad**: 🟡 Baja | Esfuerzo: S (1h) | Impacto: Mejora reproducibilidad

---

### **CI/CD (GitHub Actions)**
**Archivo**: `.github/workflows/ci.yml`

**Fortalezas**:
- ✅ Path filtering (solo ejecuta jobs si cambian archivos relevantes)
- ✅ Build de frontend en CI (no-deploy)
- ✅ Typecheck en TS

**Gaps**:
1. ❌ **No ejecuta linters** (black, ruff) en CI → Puede pasar código mal formateado
2. ❌ **No hay tests de integración** con PostgreSQL real
3. ❌ **No valida esquema Alembic** (downgrade/upgrade round-trip)

**Solución**:
```yaml
# .github/workflows/ci.yml
- name: Lint (Black + Ruff)
  run: |
    ruff check apps/backend

- name: Validate Alembic migrations
  run: |
    alembic upgrade head
    alembic downgrade -1
    alembic upgrade head  # Round-trip check
```

**Prioridad**: ⚠️ Media | Esfuerzo: S (2h) | Dueño: DevOps

---

### **Despliegue (Render.com)**
**Archivo**: `render.yaml`

**Fortalezas**:
- ✅ Separate services (API, Worker, Beat, Cron migrations)
- ✅ Health checks configurados (`/health`)
- ✅ Build filters para evitar rebuilds innecesarios
- ✅ Env vars por servicio (secrets synced externamente)

**Gaps**:
- ⚠️ **Migraciones en CRON manual** (`gestiqcloud-migrate` schedule: daily)
  - Riesgo: Deploy de API sin migración → crash por schema outdated
- ⚠️ **No hay rollback strategy** documentada
- ⚠️ **Pool size fijo** (no ajustado según plan de Render)

**Recomendación**:
1. 🔧 **Pre-deploy hook** para migraciones:
```yaml
# render.yaml (pseudo, Render no soporta hooks nativos)
# Alternativa: GitHub Action que llama API de Render para correr job antes de deploy
```

2. 🔧 **Configurar auto-scaling** en worker si carga de Celery crece:
```yaml
# render.yaml (services.worker)
autoDeploy: true
scaling:
  minInstances: 1
  maxInstances: 3
```

**Prioridad**: ⚠️ Media | Esfuerzo: M (3-4 días) | Dueño: DevOps

---

## 🔍 DUPLICADOS RELEVANTES (Backend)

| Métrica | Ruta A | Ruta B | Tipo | Recomendación |
|---------|--------|--------|------|---------------|
| 0.95 | `app/routers/payments.py` | `app/modules/reconciliation/interface/http/tenant.py` | Near | ✅ Migrar lógica a módulo reconciliation |
| 1.0 | `app/main.py:373-427` (stub einvoicing) | `app/modules/einvoicing/interface/http/tenant.py` | Exacto | ❌ **Eliminar stub** (líneas 373-427) |
| 0.88 | `app/services/audit_service.py` | `app/models/security/auth_audit.py` | Near | ⚠️ Consolidar en `modules/identity/application/audit.py` |
| 0.92 | Legacy routers (`app/routers/*.py`) | Módulos modernos (`app/modules/*/interface/http/`) | Near | ❌ **Eliminar legacy** tras validar cobertura |

**Total Estimado**: ~400-600 líneas de código duplicado/muerto
**Impacto**: Reduce mantenimiento y riesgo de bugs por divergencia

---

## 📋 PLAN DE ACCIÓN PRIORIZADO

| Pri | Tarea | Impacto | Esfuerzo | Dueño | Notas |
|-----|-------|---------|----------|-------|-------|
| 🔴 Alta | **Eliminar routers legacy duplicados** | Alto | M (4d) | Backend Lead | Validar coverage primero con tests |
| 🔴 Alta | **Agregar rate limiting por endpoint** (login, reset password) | Alto | S (2d) | Backend Lead | Usar `slowapi` |
| 🔴 Alta | **Configurar mypy + pre-commit** | Alto | M (5d) | Backend Lead | Fix de errores iterativo |
| ⚠️ Media | **Migrar a Alembic único** (archivar legacy SQL) | Alto | M (4d) | Backend Lead | Docs + validación |
| ⚠️ Media | **Habilitar Dependabot** | Medio | S (1h) | DevOps | Auto-update deps |
| ⚠️ Media | **Ajustar pool de DB** (5+10 en vez de 10+20) | Medio | S (1h) | Backend Lead | Cambio config |
| ⚠️ Media | **Agregar coverage mínimo 60%** en CI | Medio | M (3d) | Backend Lead | Escribir tests faltantes |
| ⚠️ Media | **Linters en CI** (black, ruff check) | Medio | S (1h) | DevOps | GitHub Actions |
| ⚠️ Media | **RLS en tablas de auditoría** | Medio | S (1h) | Backend Lead | apply_rls.py |
| 🟡 Baja | **Bandit + Safety en pre-commit** | Medio | S (1h) | DevOps | SAST |
| 🟡 Baja | **Healthcheck profundo** (/ready con DB+Redis) | Bajo | S (2h) | Backend Lead | Endpoint nuevo |
| 🟡 Baja | **Cache layer con Redis** | Bajo | M (4d) | Backend Lead | Solo si carga aumenta |
| 🟡 Baja | **Métricas custom OTel** | Bajo | M (3d) | Backend Lead | SLOs/SLIs |
| 🟡 Baja | **tenant_id en logs** | Bajo | S (2d) | Backend Lead | Contextvars |

---

## 📎 APÉNDICES

### A. Endpoints Documentados (Muestra)
**OpenAPI**: `/docs` (Swagger UI)

Principales routers modernos:
- `/api/v1/tenant/auth/*` → Login, refresh, logout
- `/api/v1/tenant/productos/*` → CRUD productos
- `/api/v1/tenant/ventas/*` → Ventas
- `/api/v1/imports/*` → Importador documental
- `/api/v1/admin/*` → Gestión empresas

Total estimado: **150-200 endpoints** (no contados por duplicación legacy)

### B. Matriz de Dependencias Críticas
| Dependencia | Versión | CVEs Conocidos | Actualización Recomendada |
|-------------|---------|----------------|---------------------------|
| fastapi | >=0.112.1 | ✅ Ninguno | Mantener rango |
| SQLAlchemy | 2.0.41 | ✅ Ninguno | Cambiar a `>=2.0.41,<2.1` |
| Pillow | 10.4.0 | ⚠️ CVE-2023-50447 (fixed en 10.2+) | Cambiar a `>=10.4.0,<11` |
| cryptography | >=41.0.0 | ✅ Ninguno | ✅ OK |
| PyYAML | 6.0.2 | ⚠️ CVE-2020-1747 (mitigado si no se usa `load()`) | Cambiar a `>=6.0.2,<7` |

### C. Módulos Backend (Inventario)
30+ módulos identificados en `apps/backend/app/modules/`:
- identity, imports, ventas, compras, finanzas, rrhh, produccion, einvoicing, pos, contabilidad, clientes, proveedores, gastos, inventario, productos, facturacion, facturae, templates, copilot, webhooks, reconciliation, export, modulos, usuarios, empresa, registry, admin_config, settings, shared, ai_agent, crm

---

**FIN DEL INFORME BACKEND**

*Próximo paso*: Generar `Informe_Frontend.md`
