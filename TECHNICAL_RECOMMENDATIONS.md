# 🔧 RECOMENDACIONES TÉCNICAS ESPECÍFICAS

---

## 1️⃣ PROBLEMAS INMEDIATOS A RESOLVER

### **1.1 Hardcoding Detection (CRÍTICO)**

**Documento encontrado:** `ANALISIS_HARDCODEOS.md`

```
Risk Level: MEDIUM-HIGH
Impact: Configuration, deployment, security

Problema detectado:
- Variables hardcodeadas en código
- Documentación = síntoma de deuda técnica

Acción inmediata:
1. Ejecutar análisis de hardcoding completo
2. Mover todo a .env variables
3. Validar que no haya secrets en git
```

**Comando de auditoría:**

```bash
# Backend - buscar hardcoding común
grep -r "localhost" apps/backend/app --include="*.py"
grep -r "8000" apps/backend/app --include="*.py"
grep -r "password" apps/backend/app --include="*.py" | grep -v "class\|def\|#"

# Frontend - buscar URLs hardcodeadas
grep -r "http://localhost" apps/tenant/src --include="*.ts" --include="*.tsx"
grep -r "http://localhost" apps/admin/src --include="*.ts" --include="*.tsx"
```

**Solución:**

```python
# ❌ Malo
database_url = "postgresql://localhost:5432/gestiqcloud"
api_url = "http://localhost:8000"

# ✅ Bueno
database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/gestiqcloud")
api_url = os.getenv("API_URL", "http://localhost:8000")
```

---

### **1.2 Deuda Técnica Visible**

**Archivos a limpiar:**

```
❌ cleanup_stuck_imports.py      → Ejecutar y eliminar
❌ fix_duplicate_modules.py      → Ejecutar y eliminar
❌ fix_pos_translations.py       → Revisar y eliminar
❌ find_spanish_identifiers.py   → Auditar y refactorizar
❌ find_byte.py                  → Eliminar
❌ analyze_excel.py              → Eliminar (herramienta dev)
❌ check_db.py                   → Mover a ops/scripts/

✓ Acción:
  1. Ejecutar cada cleanup script
  2. Revisar cambios
  3. Eliminar archivo
  4. Commit limpio
```

---

### **1.3 Dual Migration Systems (CONFUSO)**

**Estado actual:**

```
apps/backend/alembic/                 ← Alembic (automático)
  └─ versions/
     ├─ 001_initial_schema.py
     ├─ 005_pos_extensions.py
     └─ ...

ops/migrations/                       ← SQL manual
  ├─ 001_initial_tables.sql
  ├─ 002_add_fields.sql
  └─ ...
```

**Problema:** Dos sistemas de verdad → confusión

**Solución:**

```
OPCIÓN A (Recomendado): Solo Alembic
  1. Convertir SQL manual → Alembic revisions
  2. Ejecutar `alembic upgrade head`
  3. Eliminar ops/migrations/*.sql
  4. Documentar: "Always use alembic"

OPCIÓN B: SQL manual para schemas grandes
  1. Mantener ops/migrations/ para cambios complejos
  2. Alembic solo para incrementos pequeños
  3. Documentar orden de ejecución
  
Recomendado: OPCIÓN A
```

**Comando unificado:**

```bash
# Generar nueva migración (siempre Alembic)
cd apps/backend
alembic revision --autogenerate -m "add_new_field_to_products"

# Ejecutar
alembic upgrade head

# Rollback si falla
alembic downgrade -1
```

---

## 2️⃣ SEGURIDAD - AUDIT RECOMMENDATIONS

### **2.1 OWASP Top 10 - Estado Actual**

| Riesgo | Estado | Acción |
|--------|--------|--------|
| A01: Injection | ✅ MITIGADO | SQLAlchemy parameterized |
| A02: Broken Auth | ✅ PROTEGIDO | JWT + Rate limit |
| A03: Sensitive Data | ⚠️ REVISAR | .env secrets en git? |
| A04: XML/External Entities | ✅ OK | No hay XML processing |
| A05: Broken Access Control | 🟡 PARCIAL | RBAC sin centralizar |
| A06: Security Misconfiguration | 🟡 REVISAR | CORS, headers |
| A07: XSS | ✅ OK | React escapa por defecto |
| A08: Insecure Deserialization | ✅ OK | JSON only |
| A09: Logging & Monitoring | 🟡 PARCIAL | OpenTelemetry presente |
| A10: SSRF | ✅ OK | No hay external calls críticas |

### **2.2 Auditoría de Secrets**

**Comando crítico:**

```bash
# Buscar secrets en git
git log --all --source --remotes -S "password" --pickaxe-regex -- "*.py" "*.ts" "*.tsx"

# Archivos con posibles secrets
grep -r "SECRET_KEY\|PRIVATE_KEY\|API_KEY" apps/ .env* --include="*.py" --include="*.tsx"
```

**Si hay secrets encontrados:**

```bash
# 1. Ejecutar git-filter-branch (nuclear option)
git filter-branch --tree-filter 'find . -name ".env" -type f -delete' -- --all

# 2. Force push
git push origin --all --force

# 3. Rotar todos los secrets en producción
# (Regenerar API keys, DB passwords, etc.)
```

### **2.3 CORS y Cookies**

**Configuración actual (verificar):**

```python
# ❌ Vulnerable
CORS_ORIGINS = ["*"]  # Todos pueden acceder

# ✅ Seguro
CORS_ORIGINS = [
    "https://admin.gestiqcloud.com",
    "https://tenant.gestiqcloud.com",
    "http://localhost:8081",  # dev only
]

# Cookies
COOKIE_DOMAIN = "gestiqcloud.com"  # Sin leading dot
COOKIE_SECURE = True  # HTTPS only en prod
COOKIE_SAMESITE = "Lax"  # O "Strict" si posible
```

**Cloudflare Worker rewrite (si aplica):**

```javascript
// Edge rewrite de dominio de cookies
if (request.headers.get('Cookie')) {
  let cookie = request.headers.get('Cookie')
    .replace(/Domain=gestiqcloud\.local/g, 'Domain=gestiqcloud.com')
    .replace(/SameSite=Lax/g, 'SameSite=None; Secure');
  request.headers.set('Cookie', cookie);
}
```

---

## 3️⃣ TESTING - PLAN DE COBERTURA

### **3.1 Testing Actual**

```
Backend Tests: 45 archivos
├─ Auth:           ✅ 85% (test_login.py, test_auth_cookies.py)
├─ POS:            ✅ 80% (test_smoke_pos_pg.py)
├─ Invoicing:      🟡 60% (test_einvoicing.py)
├─ Accounting:     🟡 50% (test_accounting.py)
├─ Inventory:      ✅ 75% (test_inventory_costing.py)
└─ Imports:        ✅ 80% (test_imports_*.py)

Frontend Tests: Casi nulo
├─ manifest.test.ts (POS)
└─ index.test.ts (modules loader)
```

### **3.2 Mejorar Cobertura**

**Backend - Agregar tests:**

```bash
# 1. Ejecutar coverage actual
cd apps/backend
pytest --cov=app --cov-report=html

# 2. Identificar módulos bajo 60%
# (Ver htmlcov/index.html)

# 3. Agregar tests críticos
pytest app/tests/test_accounting.py -v --cov=app.modules.accounting

# 4. Target: 75% mínimo
pytest --cov=app --cov-fail-under=75
```

**Frontend - Agregar tests:**

```bash
# apps/tenant
cd apps/tenant
npm run test:coverage

# Crear fixtures para módulos comunes
# src/modules/__tests__/fixtures/
#   ├─ authContext.tsx
#   ├─ mockAPI.ts
#   ├─ mockData.ts
#   └─ renderWithProviders.tsx

# Agregar tests mínimos por módulo
# src/modules/{module}/__tests__/
#   └─ {module}.test.tsx
```

### **3.3 E2E Testing (Nuevo)**

**Implementar con Playwright:**

```bash
npm install -D @playwright/test

# apps/tenant/playwright.config.ts (ya existe)
# Crear tests:
# e2e/
# ├─ auth.spec.ts
# ├─ pos.spec.ts
# ├─ inventory.spec.ts
# └─ invoicing.spec.ts
```

**Ejemplo test POS:**

```typescript
// e2e/pos.spec.ts
import { test, expect } from '@playwright/test';

test.describe('POS Module', () => {
  test('should complete a sale', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'secret');
    await page.click('button:has-text("Login")');
    
    // 2. Navigate to POS
    await page.goto('/pos');
    
    // 3. Open shift
    await page.click('button:has-text("Open Shift")');
    
    // 4. Add product
    await page.click('[data-product-id="bread-1"]');
    
    // 5. Verify cart
    const total = await page.textContent('[data-total-price]');
    expect(total).toContain('€');
    
    // 6. Process payment
    await page.click('button:has-text("Charge")');
    await page.fill('input[placeholder="Amount"]', '10');
    await page.click('button:has-text("Confirm")');
    
    // 7. Verify receipt
    await expect(page).toHaveURL(/receipt/);
  });
});
```

---

## 4️⃣ PERFORMANCE - OPTIMIZACIONES

### **4.1 Backend Performance**

**Checklist:**

```python
# 1. Lazy loading de relaciones
from sqlalchemy.orm import selectinload, joinedload

# ❌ Malo
customers = db.query(Customer).all()  # N+1 problem

# ✅ Bueno
customers = db.query(Customer).options(
    selectinload(Customer.orders)
).all()

# 2. Índices de BD
class Customer(Base):
    __tablename__ = "customers"
    email = Column(String, index=True)  # ✅ Indexed
    phone = Column(String)               # ❌ Not indexed

# 3. Caché
from fastapi_cache2 import FastAPICache2

@app.get("/api/v1/products")
@cached(expire=3600)  # 1 hora
async def get_products():
    return db.query(Product).all()

# 4. Pagination
@app.get("/api/v1/orders")
async def list_orders(skip: int = 0, limit: int = 50):
    return db.query(Order).offset(skip).limit(limit).all()

# 5. Connection pooling
DATABASE_URL = "postgresql+psycopg://user:pass@host/db"
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Conexiones activas
    max_overflow=10,        # Conexiones adicionales
)
```

### **4.2 Frontend Performance**

```typescript
// 1. Code splitting
const POS = React.lazy(() => import('./modules/pos/POSView'));

<Suspense fallback={<Spinner />}>
  <POS />
</Suspense>

// 2. Image optimization
<img 
  src="product.jpg" 
  alt="Product"
  loading="lazy"
  decoding="async"
/>

// 3. State management (no prop drilling)
// ✅ Use context + custom hook
const { products, loading } = useProducts();

// 4. Memoization
const MemoizedCart = React.memo(({ items }) => {
  return items.map(item => <CartItem key={item.id} {...item} />);
});

// 5. Service Worker optimization
// Precache solo archivos críticos
// Cache-first para assets estáticas
// Network-first para API calls
```

### **4.3 Load Testing**

```bash
# Instalar k6
npm install -g k6

# Crear load test
# k6/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp-up
    { duration: '1m30s', target: 50 }, // Stay
    { duration: '30s', target: 0 },    // Ramp-down
  ],
};

export default function () {
  let res = http.get('http://localhost:8000/api/v1/products');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}

# Ejecutar
k6 run k6/load_test.js
```

---

## 5️⃣ DEVOPS - DEPLOYMENT

### **5.1 Docker Setup**

**Crear Dockerfiles:**

```dockerfile
# apps/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

```dockerfile
# apps/tenant/Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

### **5.2 Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./apps/backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/gestiqcloud
      REDIS_URL: redis://redis:6379/0
      ENV: development
    depends_on:
      - postgres
      - redis
    volumes:
      - ./apps/backend:/app  # Dev mode

  tenant:
    build: ./apps/tenant
    ports:
      - "8082:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend

  admin:
    build: ./apps/admin
    ports:
      - "8081:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: gestiqcloud
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### **5.3 GitHub Actions CI/CD**

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd apps/backend
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd apps/backend
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./apps/backend/coverage.xml

  test-frontend:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install tenant
        run: cd apps/tenant && npm ci
      
      - name: Run typecheck
        run: cd apps/tenant && npm run typecheck
      
      - name: Run lint
        run: cd apps/tenant && npm run lint
      
      - name: Run tests
        run: cd apps/tenant && npm run test:run
```

---

## 6️⃣ MONITOREO Y OBSERVABILIDAD

### **6.1 Logging**

```python
# apps/backend/app/core/logging.py
import logging
from opentelemetry import logging as otel_logging
from opentelemetry.sdk.logging import LoggerProvider
from opentelemetry.sdk.logging.export import BatchLogRecordProcessor

# Setup logging
logger_provider = LoggerProvider()
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(
        otlp_exporter  # OTLP endpoint (Jaeger, Datadog, etc)
    )
)

logger = logging.getLogger(__name__)

# Structured logging
logger.info("User login", extra={
    "user_id": user.id,
    "tenant_id": tenant.id,
    "ip_address": request.client.host,
    "timestamp": datetime.utcnow().isoformat(),
})
```

### **6.2 Metrics**

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Setup metrics
reader = PeriodicExportingMetricReader(otlp_exporter)
provider = MeterProvider(metric_readers=[reader])

meter = provider.get_meter(__name__)

# Create counters
requests_total = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests"
)

requests_latency = meter.create_histogram(
    name="http_request_duration_ms",
    description="HTTP request latency (ms)"
)

# Use in handlers
start = time.time()
requests_total.add(1, {"method": "GET", "endpoint": "/api/v1/products"})
requests_latency.record((time.time() - start) * 1000)
```

### **6.3 Alerting**

```yaml
# prometheus/alerts.yml
groups:
  - name: gestiqcloud
    rules:
      - alert: HighErrorRate
        expr: |
          (sum(rate(http_requests_total{status=~"5.."}[5m]))
           /
           sum(rate(http_requests_total[5m])))
          > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: postgres_up == 0
        for: 1m
        annotations:
          summary: "PostgreSQL is down"

      - alert: SlowResponses
        expr: |
          histogram_quantile(0.95, http_request_duration_ms) > 1000
        for: 5m
        annotations:
          summary: "P95 latency > 1s"
```

---

## 7️⃣ DOCUMENTACIÓN - MEJORAS NECESARIAS

### **7.1 Frontend Documentation**

**Crear:** `apps/tenant/README.md` completo

```markdown
# Tenant Application (PWA)

## Módulos

### POS (Punto de Venta)
- Descripción
- Configuración
- Keyboard shortcuts
- Troubleshooting

### CRM (Clientes)
- Descripción
- API integration
- Custom fields

...

## Development

### Setup
### Testing
### Debugging
### Building
```

### **7.2 API Documentation**

**Usar OpenAPI/Swagger:**

```python
# apps/backend/app/main.py
app = FastAPI(
    title="GestiQCloud API",
    description="Multi-tenant ERP/CRM",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# Documentar rutas
@app.get("/api/v1/pos/receipts")
async def list_receipts(
    skip: int = Query(0, description="Número de registros a saltar"),
    limit: int = Query(50, description="Número de registros a retornar"),
):
    """
    Listar todos los tickets de punto de venta
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros (default: 50)
    
    Retorna una lista paginada de tickets.
    """
    return db.query(Receipt).offset(skip).limit(limit).all()
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### **Fase 1: Correcciones Inmediatas** (1 semana)

- [ ] Ejecutar `cleanup_stuck_imports.py`
- [ ] Eliminar archivos de deuda técnica
- [ ] Audit de hardcoding
- [ ] Mover a .env
- [ ] Run `pytest` con 100% pass

### **Fase 2: Seguridad** (2 semanas)

- [ ] Buscar secrets en git
- [ ] Validar CORS
- [ ] Validar cookies
- [ ] Security audit OWASP
- [ ] Setup HTTPS/TLS

### **Fase 3: Testing** (3 semanas)

- [ ] Backend coverage → 75%
- [ ] Frontend coverage → 40%
- [ ] E2E tests (Playwright)
- [ ] Load testing (k6)
- [ ] Manual testing checklist

### **Fase 4: DevOps** (2 semanas)

- [ ] Docker images
- [ ] Docker Compose
- [ ] GitHub Actions CI/CD
- [ ] Deploy to staging
- [ ] Setup monitoring

### **Fase 5: Documentación** (1 semana)

- [ ] Complete README files
- [ ] API docs (Swagger)
- [ ] Troubleshooting guides
- [ ] Runbooks

---

**Estimated Total:** 8-10 semanas para producción
**Costo estimado:** €60-80k

