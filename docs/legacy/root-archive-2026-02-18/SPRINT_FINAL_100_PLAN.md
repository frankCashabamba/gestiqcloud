# 🎯 PLAN FINAL 100% - COMPLETAR GESTIQCLOUD

**Fecha:** 2026-02-16
**Estado:** ~95% completo → Falta cerrar las últimas tareas críticas

---

## 📋 TAREAS ORDENADAS POR PRIORIDAD

### FASE 1: VALIDACIÓN (2-3 horas)

#### 1.1 Verificar estado de tests
```bash
# Activar venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Ver tests disponibles
python -m pytest --collect-only -q 2>&1 | grep "test_" | wc -l

# Ejecutar todos los tests
python -m pytest tests/ -v --tb=short

# Ver cobertura
python -m pytest tests/ --cov=apps --cov-report=html
```

#### 1.2 Ejecutar linters y formateadores
```bash
# Ruff (linting)
ruff check . --select=E,F,W,C,N --show-fixes

# Black (formatting)
black --check .

# Isort (imports)
isort --check-only .

# Mypy (type checking)
mypy apps/ --no-error-summary 2>&1 | head -50
```

---

### FASE 2: FIXES CRÍTICOS (4-6 horas)

#### 2.1 Activar Mypy como bloqueante
**Archivo:** `pyproject.toml`
```toml
[tool.mypy]
# Cambiar de:
exit_code = 0  # --exit-zero
# A:
exit_code = 1  # Forzar bloqueante
warn_unused_ignores = true
```

#### 2.2 Tests que faltan (Inventory + Sales)
```bash
# Sales: discount_pct endpoint
# File: apps/sales/application/use_cases.py
# Agregar:
def calculate_order_total_with_discount(
    order_items: List[OrderItemIn],
    discount_pct: float = 0.0
) -> Decimal:
    """Calcula total con descuento."""
    subtotal = sum(item.quantity * item.unit_price for item in order_items)
    discount = subtotal * (discount_pct / 100)
    return subtotal - discount

# Inventory: LIFO costing
# File: apps/inventory/application/services.py
# Implementar método LIFO (complementar FIFO/AVG existente)
```

#### 2.3 Frontend tests
```bash
# E2E tests existentes
cd e2e/
npm test  # Ejecutar Playwright

# Ver qué falta
grep -r "test(" --include="*.tsx" apps/frontend/src/
```

---

### FASE 3: COMPLETAR FUNCIONALIDADES (3-4 horas)

#### 3.1 Inventory: Stock transfers
**Archivo:** `apps/inventory/domain/models.py`
```python
class StockTransfer(BaseModel):
    """Transferencia entre almacenes."""
    id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    product_id: UUID
    quantity: Decimal
    status: TransferStatus  # DRAFT, IN_TRANSIT, COMPLETED
    created_at: datetime
```

#### 3.2 Sales: Invoice from order
**Archivo:** `apps/sales/presentation/api.py`
```python
@router.post("/orders/{order_id}/invoice")
async def create_invoice_from_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: InvoiceService = Depends()
):
    """Crear factura desde orden de venta."""
    # Validar que orden esté confirmada
    # Crear factura con líneas de la orden
    # Linkear factura a orden
    pass
```

#### 3.3 CI/CD: Habilitar en GitHub Actions
**Archivo:** `.github/workflows/ci.yml`
```yaml
- name: Run type checking (Mypy)
  run: mypy apps/ --no-error-summary

- name: Run backend tests
  run: pytest tests/ -v --cov=apps --cov-fail-under=70

- name: Run E2E tests
  run: npm run e2e
```

---

### FASE 4: DEPLOYMENT (2-3 horas)

#### 4.1 Render deployment setup
```bash
# Validar render.yaml
cat render.yaml | grep -E "buildCommand|startCommand|env"

# Test migrations localmente
python ops/migrations/run_migrations.py --dry-run

# Test startup validation
python apps/backend/startup_validation.py
```

#### 4.2 Environment variables
```bash
# Verificar .env.render.example tiene todas las vars
diff -u <(grep "^[A-Z_]*=" .env.example | cut -d= -f1 | sort) \
         <(grep "^[A-Z_]*=" .env.render.example | cut -d= -f1 | sort)
```

#### 4.3 Database migrations
```bash
# Validar que todas las migrations en ops/migrations/ sean idempotentes
for file in ops/migrations/*.sql; do
  echo "=== $file ==="
  grep -E "CREATE|ALTER|DROP" "$file"
done
```

---

### FASE 5: DOCUMENTACIÓN (1-2 horas)

#### 5.1 README.md actualizado
- [ ] Instrucciones setup (local + Render)
- [ ] Estructura módulos
- [ ] API docs link
- [ ] Contribuyendo

#### 5.2 API docs (Swagger)
```bash
# Validar que FastAPI genera OpenAPI correcto
curl http://localhost:8000/openapi.json | jq . > openapi.json
```

#### 5.3 Runbook para deployment
```markdown
# Runbook: Deploy a Render

## Pre-deploy
1. Merge a main
2. Ejecutar tests: pytest -v
3. Black/Ruff clean

## Deploy
1. Push a main
2. Render auto-builds desde render.yaml
3. Validar migraciones en logs

## Post-deploy
1. Verificar uptime en Sentry
2. Revisar error logs
3. Smoke test API
```

---

## ✅ CHECKLIST FINAL

### Código
- [ ] Ruff clean (`ruff check .`)
- [ ] Black clean (`black --check .`)
- [ ] Isort clean (`isort --check-only .`)
- [ ] Mypy bloqueante activado
- [ ] Tests passing (70%+ coverage)
- [ ] E2E tests passing

### Backend
- [ ] Identity tests: 17+ passing
- [ ] Invoicing tests: 10+ passing
- [ ] Sales tests: 8+ passing (con discount_pct)
- [ ] Inventory tests (con LIFO)
- [ ] Accounting tests: 15+ passing
- [ ] Finance tests: 16+ passing
- [ ] HR tests: 17+ passing
- [ ] E-Invoicing tests: 22+ passing
- [ ] Webhooks tests: 8+ passing
- [ ] Notifications tests: 5+ passing

### Frontend
- [ ] Build sin warnings
- [ ] E2E tests passing (POS, Invoicing, Inventory, Webhooks)
- [ ] Lighthouse >90

### Deployment
- [ ] render.yaml validado
- [ ] ops/migrations/ completo
- [ ] Environment variables validadas
- [ ] Startup validation passing
- [ ] SSL/TLS ready

### Documentación
- [ ] README actualizado
- [ ] API docs disponibles
- [ ] Runbooks completos
- [ ] CONTRIBUTING.md

---

## 🚀 ÚLTIMO PASO: GO-LIVE

```bash
# 1. Commit final
git add .
git commit -m "SPRINT FINAL: Sistema 100% listo para Render"

# 2. Tag release
git tag -a v1.0.0 -m "Production release"

# 3. Push
git push origin main --tags

# 4. Render auto-deploys desde main
# Ver en: https://dashboard.render.com
```

---

## 📊 ESTIMACIÓN

| Fase | Tiempo | Status |
|------|--------|--------|
| 1. Validación | 2-3h | ⏳ |
| 2. Fixes críticos | 4-6h | ⏳ |
| 3. Funcionalidades | 3-4h | ⏳ |
| 4. Deployment | 2-3h | ⏳ |
| 5. Documentación | 1-2h | ⏳ |
| **TOTAL** | **12-18h** | 🔥 |

**Tiempo real: 1-2 días de trabajo intenso**

---

## 🎯 OBJETIVO FINAL

```
✅ TODOS LOS TESTS PASSING
✅ CÓDIGO LIMPIO (Ruff + Black + Mypy)
✅ DEPLOYMENT A RENDER FUNCIONAL
✅ DOCUMENTACIÓN COMPLETA
✅ 🚀 SISTEMA EN PRODUCCIÓN
```
