# 📋 PLAN MAESTRO DE DESARROLLO — GestiqCloud ERP/POS/SaaS

> **Documento generado:** 17 Marzo 2026
> **Alcance:** Auditoría completa + Integración IA — Plan unificado de desarrollo
> **Meta:** Llevar el sistema de 78-82% a 95%+ de madurez para producción masiva

---

## ÍNDICE

1. [Estado Actual Consolidado](#1-estado-actual-consolidado)
2. [Inventario Completo de Tareas](#2-inventario-completo-de-tareas)
3. [Dependencias entre Tareas](#3-dependencias-entre-tareas)
4. [Plan de Ejecución por Semanas](#4-plan-de-ejecución-por-semanas)
5. [Detalle Técnico por Tarea](#5-detalle-técnico-por-tarea)
6. [Módulos Comerciales y Sectores](#6-módulos-comerciales-y-sectores)
7. [Métricas de Éxito](#7-métricas-de-éxito)
8. [Estado de Implementación (Auditoría 17-Mar-2026)](#8-estado-de-implementación-auditoría-17-mar-2026)

---

## 1. ESTADO ACTUAL CONSOLIDADO

### 1.1 Lo que SÍ está resuelto (NO tocar)
| Componente | Estado | Archivos clave |
|-----------|--------|----------------|
| RLS completo 60+ tablas | ✅ | `db/rls.py`, migraciones SQL |
| 88+ migraciones idempotentes con SHA-256 + rollback | ✅ | `ops/migrations/` |
| Auth JWT + refresh rotation + RBAC + cookies HttpOnly | ✅ | `modules/identity/` |
| Factory IA con 3 providers + fallback chain | ✅ | `services/ai/factory.py` |
| Recovery Manager IA con 4 estrategias reales | ✅ | `services/ai/recovery.py` |
| Logging IA completo con audit trail | ✅ | `services/ai/logging.py`, `models/ai_log.py` |
| Importador con OCR + Vision fallback + clasificación | ✅ | `modules/importador/ai_classifier.py` |
| POS checkout real con FIFO/LIFO/AVG + stock down | ✅ | `modules/pos/interface/http/receipts.py` |
| Compras → Inventario conectado con costeo | ✅ | `modules/purchases/` |
| Ventas → Facturación con conversión | ✅ | `modules/sales/` |
| Module Catalog con discovery + dependencias | ✅ | `modules/modules_catalog/` |
| Feature Flags jerárquicos | ✅ | `modules/feature_flags/` |
| Tests: 70+ archivos (NO 7 como decía la auditoría) | ✅ | `app/tests/` |
| Health check profundo en `/ready` (DB+Redis+Celery) | ✅ | `main.py:414-466` |
| Payment providers (Stripe, Kushki, Payphone) | ✅ | `services/payments/` |

### 1.2 Correcciones a la auditoría original
| Afirmación de la auditoría | Realidad en el código |
|---------------------------|----------------------|
| "Solo 7 archivos de test" | **70+ archivos** en `app/tests/` + `tests/` |
| "Health check superficial" | `/ready` verifica DB + Redis + Celery broker. `/healthz` sí es superficial pero `/ready` es completo |
| "Sin health check de IA" | Existe `/health/ai` en `routers/ai_health.py` |
| "Sin rate limiting" | Existe `test_rate_limit.py` — hay implementación parcial |

### 1.3 Lo que SÍ requiere trabajo (confirmado en código)

#### 🔴 CRÍTICO — Bloquean producción masiva
| ID | Problema | Archivo | Impacto |
|----|----------|---------|---------|
| C1 | **Use Cases POS son stubs** — 6 clases retornan dicts estáticos, lógica real en `receipts.py` (800+ líneas SQL raw) | `pos/application/use_cases.py` | Testing imposible, bugs difíciles |
| C2 | **Use Cases Inventario son stubs** — 6 clases retornan dicts vacíos, lógica real en HTTP handlers | `inventory/application/use_cases.py` | Misma situación |
| C3 | **Pipeline POS→Contabilidad no es automático** — `generate_accounting_for_closed_shift` es endpoint separado, no se ejecuta automáticamente al cerrar turno | `pos/interface/http/shifts.py:700-897` | Cierre incompleto |
| C4 | **Sin concepto de Sucursal (Branch)** — Warehouse existe pero no hay entidad que vincule warehouse + POS register + caja + usuarios | Sin archivo | Multi-sucursal roto |
| C5 | **Sin billing/suscripciones backend** — Payment providers existen para cobrar facturas a clientes, pero no hay sistema para cobrar los MÓDULOS a los tenants | `services/payments/` (solo invoice payments) | No se puede monetizar |
| C6 | **Copilot sin contexto de módulo** — El chat no sabe en qué pantalla está el usuario ni qué módulo tiene abierto | `copilot/interface/http/tenant.py:172-176` | IA genérica e inútil |

#### 🟡 IMPORTANTE — Reducen calidad
| ID | Problema | Archivo | Impacto |
|----|----------|---------|---------|
| I1 | **`datetime.utcnow()` deprecated** — Usado en 20+ archivos del módulo IA, POS, logging | Múltiples | Warning en Python 3.12+ |
| I2 | **`logger.info` en `ensure_tenant` cada request** — 3 llamadas INFO por request | `middleware/tenant.py:54,60,72` | Logs saturados en producción |
| I3 | **`create_invoice_draft` usa `int(tenant_id)`** — Rompe con UUIDs | `copilot/services.py:209` + `tenant.py:125-128` | Crash en sistema UUID |
| I4 | **Solo 6 topics en copilot** — Sin POS hoy, gastos, producción, compras pendientes | `copilot/services.py:98-186` | Copilot limitado |
| I5 | **Sin streaming para chat IA** — Espera respuesta completa (2-5s sin feedback) | `copilot/interface/http/tenant.py:184-255` | UX mala |
| I6 | **Historial de chat efímero** — Se pierde al recargar página | `CopilotChatWidget.tsx:22` | Frustración del usuario |
| I7 | **Sin rate limit por tenant para IA** — Un tenant puede agotar presupuesto de API | Sin implementar | Riesgo financiero |
| I8 | **PII no se filtra en contexto del chat** — `pii_mask_row()` existe pero no se usa en el chat | `copilot/services.py` | Riesgo de privacidad |
| I9 | **System prompts duplicados** — OpenAI y OVH providers copian mismo `_get_system_prompt` | `openai.py:133` + `ovhcloud.py:161` | Mantenimiento |
| I10 | **Template ticket POS 80mm** — Sin template de impresión térmica estándar | `modules/printing/` | Limitación funcional |

#### 🟢 DESEABLE — Mejoran competitividad
| ID | Problema | Archivo | Impacto |
|----|----------|---------|---------|
| D1 | Sin alertas de caducidad (farmacia/alimentos) | Inventario | Sector farmacia bloqueado |
| D2 | Sin módulo de mesas/comandas (restaurante) | No existe | Sector restaurante limitado |
| D3 | Sin variantes de producto (talla/color) | Productos | Sector ferretería/ropa limitado |
| D4 | Sin multi-moneda con conversión real | Finanzas | Internacional limitado |
| D5 | Sin MFA (multi-factor authentication) | Auth | Seguridad enterprise |
| D6 | Sin backup automatizado (pg_dump/WAL) | Ops | Riesgo de datos |
| D7 | Sin log rotation en producción | Ops | `backend.log` crece sin límite |
| D8 | Sin onboarding wizard completo | Tenant | Activación de clientes lenta |
| D9 | Sin documentación API enriquecida | Docs | Partners no pueden integrar |
| D10 | WhatsApp y Slack notifiers son stubs | `ai_agent/notifier.py:149,197` | Notificaciones incompletas |

---

## 2. INVENTARIO COMPLETO DE TAREAS

### BLOQUE A: Calidad de Código (Refactoring)

| Task | Descripción | Archivos afectados | Esfuerzo | Prioridad |
|------|------------|-------------------|----------|-----------|
| **A1** | Refactorizar `receipts.py` checkout: extraer lógica a `CheckoutService` con transacciones atómicas | `pos/interface/http/receipts.py` → nuevo `pos/application/checkout_service.py` | 5 días | P0 |
| **A2** | Implementar Use Cases POS reales: mover lógica de handlers a use_cases, inyectar repositorios | `pos/application/use_cases.py` + handlers | 3 días | P0 |
| **A3** | Implementar Use Cases Inventario reales: conectar con stock_items, stock_moves, costeo | `inventory/application/use_cases.py` + handlers | 3 días | P0 |
| **A4** | Pipeline automático: `close_shift` → journal entries → cierre de caja en una transacción | `pos/interface/http/shifts.py` + `accounting/journal_service.py` | 2 días | P1 |
| **A5** | Migrar `datetime.utcnow()` → `datetime.now(UTC)` en todo el backend | 20+ archivos | 2h | P2 |
| **A6** | Cambiar `logger.info` → `logger.debug` en `ensure_tenant` | `middleware/tenant.py:54,60,72` | 15min | P1 |
| **A7** | Unificar `_get_system_prompt` en `base.py` para evitar duplicación | `base.py`, `openai.py`, `ovhcloud.py` | 1h | P3 |
| **A8** | Fix `create_invoice_draft` UUID — quitar `int()` | `copilot/services.py:209` + `tenant.py:125-128` | 30min | P1 |

### BLOQUE B: Funcionalidad Faltante (Nuevos features)

| Task | Descripción | Archivos a crear/modificar | Esfuerzo | Prioridad |
|------|------------|---------------------------|----------|-----------|
| **B1** | Concepto de Sucursal (Branch): modelo + migración + vincular warehouse + POS register + caja + usuarios | Nuevo módulo `branches/` + migración SQL | 5 días | P1 |
| **B2** | Billing/suscripciones backend: modelos Plan + Subscription + endpoints para upgrade/downgrade + Stripe recurring | Nuevo: `modules/billing/` backend | 8 días | P1 |
| **B3** | Template ticket POS 80mm térmico estándar | `modules/printing/templates/` | 2 días | P1 |
| **B4** | Alertas de caducidad: query productos con lotes próximos a vencer + notificación | `modules/inventory/` + `modules/notifications/` | 2 días | P2 |
| **B5** | Rate limit por tenant (no global) para todos los endpoints | Middleware nuevo o modificar existente | 2 días | P1 |
| **B6** | Backup automatizado: script pg_dump + cron/Celery beat + verificación | `ops/scripts/backup.sh` + tarea Celery | 1 día | P2 |
| **B7** | Log rotation con logrotate o en código | `ops/` + config | 2h | P2 |
| **B8** | Módulo de mesas/comandas para restaurante | Nuevo: `modules/restaurant/` | 10 días | P3 |
| **B9** | Variantes de producto (talla, color, medida) | `modules/products/` + migración | 5 días | P3 |
| **B10** | Multi-moneda con conversión real | `modules/finances/` + migración | 5 días | P3 |
| **B11** | MFA (TOTP + recovery codes) | `modules/identity/` | 3 días | P3 |
| **B12** | Onboarding wizard completo paso a paso | Frontend + backend endpoints | 3 días | P3 |
| **B13** | Documentación API enriquecida (OpenAPI + ejemplos) | `docs/api/` | 3 días | P3 |
| **B14** | Implementar notifiers WhatsApp (Twilio) y Slack reales | `ai_agent/notifier.py` | 2 días | P3 |

### BLOQUE C: Tests

| Task | Descripción | Archivos a crear | Esfuerzo | Prioridad |
|------|------------|-----------------|----------|-----------|
| **C-T1** | Tests unitarios POS checkout (después de refactor A1) | `tests/test_pos_checkout.py` | 2 días | P0 |
| **C-T2** | Tests unitarios receive_purchase con costeo | `tests/test_purchase_receive.py` | 1 día | P1 |
| **C-T3** | Tests flujo login → token → refresh → logout | `tests/test_auth_flow.py` | 1 día | P1 |
| **C-T4** | Tests cierre de turno → contabilidad automática | `tests/test_shift_accounting.py` | 1 día | P1 |
| **C-T5** | Tests copilot contextual (después de refactor IA) | `tests/test_copilot_context.py` | 1 día | P2 |
| **C-T6** | Tests E2E Playwright: POS checkout flow completo | `e2e/tests/pos_checkout.spec.ts` | 2 días | P2 |
| **C-T7** | Tests E2E: flujo de compra → recepción → inventario | `e2e/tests/purchase_flow.spec.ts` | 2 días | P2 |

### BLOQUE D: Integración IA

| Task | Descripción | Archivos afectados | Esfuerzo | Prioridad |
|------|------------|-------------------|----------|-----------|
| **D-IA1** | Agregar `current_module` a ChatIn + pasar desde frontend | `tenant.py:172` + `CopilotChatWidget.tsx` + `CompanyShell.tsx` | 4h | P0 |
| **D-IA2** | Crear `CopilotContextBuilder` con loaders por módulo (POS, Inventario, Compras, Ventas, Producción, Gastos, Finanzas) | Nuevo: `copilot/context_builder.py` | 1 día | P0 |
| **D-IA3** | Agregar 5+ topics a `query_readonly`: `pos_hoy`, `gastos_mes`, `produccion_activa`, `compras_pendientes`, `prediccion_reorden` | `copilot/services.py` | 4h | P1 |
| **D-IA4** | Agregar datos del tenant al system prompt (sector, país, moneda) | `tenant.py` + `context_builder.py` | 2h | P1 |
| **D-IA5** | Aplicar `pii_mask_row()` en todo contexto enviado a IA | `context_builder.py` | 1h | P1 |
| **D-IA6** | Rate limit por tenant para `/ai/*` (20 req/min chat, 5/min suggestions) | Middleware + `tenant.py` | 4h | P1 |
| **D-IA7** | Predicción de reorden: query consumo/día + stock actual + alert IA | `copilot/services.py` nuevo topic | 4h | P2 |
| **D-IA8** | Detección de anomalías en ventas POS (< 60% promedio) | `copilot/services.py` + IA | 4h | P2 |
| **D-IA9** | Resumen ejecutivo diario via Celery + Email | Nuevo: `workers/ai_tasks.py` | 1 día | P2 |
| **D-IA10** | Streaming SSE para `/ai/chat` + EventSource en frontend | `tenant.py` + `CopilotChatWidget.tsx` | 3 días | P2 |
| **D-IA11** | Persistir historial de chat en BD (modelo `CopilotConversation`) | Nuevo modelo + migración + `services.py` | 2 días | P2 |
| **D-IA12** | Sugerencias contextuales en widget según módulo activo | `CopilotChatWidget.tsx` | 4h | P2 |
| **D-IA13** | Clasificación automática de gastos | `copilot/services.py` + IA | 4h | P3 |
| **D-IA14** | Sugerencia de precios basada en recetas + margen objetivo | `copilot/services.py` + IA | 1 día | P3 |
| **D-IA15** | User feedback (👍👎) en respuestas del chat → `ai_request_logs.user_feedback` | `CopilotChatWidget.tsx` + `tenant.py` | 4h | P3 |
| **D-IA16** | Dashboard métricas IA: requests/día, costo estimado, error rate | Nuevo endpoint + frontend | 1 día | P3 |

---

## 3. DEPENDENCIAS ENTRE TAREAS

```
A1 (Refactor checkout) ──→ C-T1 (Tests POS checkout)
A1 ──→ A2 (Use Cases POS reales)
A2 ──→ A4 (Pipeline shift→contabilidad)
A4 ──→ C-T4 (Tests cierre→contabilidad)

A3 (Use Cases Inventario) ──→ C-T2 (Tests receive)

D-IA1 (current_module) ──→ D-IA2 (ContextBuilder) ──→ D-IA4 (tenant datos)
D-IA2 ──→ D-IA5 (PII mask)
D-IA2 ──→ D-IA3 (topics nuevos)
D-IA10 (streaming) ──→ D-IA11 (historial BD)
D-IA6 (rate limit IA) es independiente

B1 (Sucursales) es independiente
B2 (Billing) es independiente
B5 (Rate limit tenant) ──→ D-IA6 (Rate limit IA)
```

---

## 4. PLAN DE EJECUCIÓN POR SEMANAS

### 📅 FASE 1: Fundamentos (Semanas 1-3) — Meta: 85%

#### Semana 1: Refactoring crítico + Quick wins IA
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | A8: Fix `create_invoice_draft` UUID (30min) | D-IA1: Agregar `current_module` a ChatIn + frontend (4h) |
| | A6: `logger.info` → `logger.debug` en `ensure_tenant` (15min) | |
| **M** | D-IA2: Crear `CopilotContextBuilder` (POS, Inventario, Compras) | D-IA3: Agregar topics `pos_hoy`, `gastos_mes`, `compras_pendientes` |
| **X** | D-IA4: Datos tenant al system prompt (sector, país, moneda) | D-IA5: Aplicar `pii_mask_row` en ContextBuilder |
| | D-IA5: PII mask en todo contexto IA | D-IA6: Rate limit por tenant para `/ai/*` |
| **J** | A1: Iniciar refactor `receipts.py` — extraer `CheckoutService` | A1: Continuar refactor checkout |
| **V** | A1: Completar refactor checkout | A5: Migrar `datetime.utcnow()` → `datetime.now(UTC)` (2h) |

#### Semana 2: Use Cases reales + Tests
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | A2: Implementar Use Cases POS reales (OpenShift, CreateReceipt) | A2: CheckoutReceipt + CloseShift use cases |
| **M** | A2: POS_StockIntegration + POS_AccountingIntegration reales | A3: Implementar Use Cases Inventario reales |
| **X** | A3: ReceiveStock + AdjustStock + TransferStock reales | A4: Pipeline automático close_shift → journal entries |
| **J** | C-T1: Tests unitarios POS checkout (post-refactor) | C-T1: Continuar tests POS |
| **V** | C-T2: Tests receive_purchase con costeo | C-T4: Tests cierre turno → contabilidad |

#### Semana 3: Funcionalidad faltante P1
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | B3: Template ticket POS 80mm térmico | B3: Completar template + test impresión |
| **M** | B5: Rate limit por tenant (middleware) | B5: Tests rate limit |
| **X** | D-IA7: Predicción de reorden | D-IA8: Detección anomalías ventas |
| **J** | C-T3: Tests flujo auth (login→token→refresh→logout) | B6: Backup automatizado + script |
| **V** | B7: Log rotation | A7: Unificar system prompts + revisión semana |

### 📅 FASE 2: Copilot Inteligente + Sucursales (Semanas 4-6) — Meta: 90%

#### Semana 4: IA avanzada
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | D-IA10: Streaming SSE backend (`StreamingResponse`) | D-IA10: Frontend `EventSource` |
| **M** | D-IA10: Completar streaming + testing | D-IA11: Modelo `CopilotConversation` + migración |
| **X** | D-IA11: Persistir historial en BD | D-IA12: Sugerencias contextuales en widget por módulo |
| **J** | D-IA9: Resumen ejecutivo diario (Celery task + email) | D-IA9: Testing resumen |
| **V** | D-IA15: User feedback 👍👎 en chat | D-IA13: Clasificación automática gastos |

#### Semana 5: Sucursales (Branch)
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | B1: Diseño modelo Branch (migración SQL) | B1: Modelo SQLAlchemy + relaciones |
| **M** | B1: CRUD endpoints Branch | B1: Vincular warehouse + POS register |
| **X** | B1: Vincular caja + usuarios a Branch | B1: Frontend — selector de sucursal |
| **J** | B1: Tests Branch | B4: Alertas de caducidad inventario |
| **V** | B4: Notificación de productos próximos a vencer | C-T5: Tests copilot contextual |

#### Semana 6: Billing/Suscripciones (inicio)
| Día | Mañana | Tarde |
|-----|--------|-------|
| **L** | B2: Modelos Plan + Subscription (migración) | B2: Modelo SQLAlchemy + CRUD |
| **M** | B2: Endpoints: create/upgrade/downgrade plan | B2: Integración Stripe Subscriptions API |
| **X** | B2: Webhook Stripe para subscription events | B2: Enforcement — middleware que valida plan activo |
| **J** | B2: Frontend — página de planes/precios | B2: Frontend — gestión de suscripción |
| **V** | B2: Tests billing | C-T6: E2E Playwright — POS checkout flow |

### 📅 FASE 3: Completitud y Pulido (Semanas 7-10) — Meta: 95%

#### Semana 7: E2E + Producción
| Día | Tarea |
|-----|-------|
| **L-M** | C-T6: E2E POS checkout completo + C-T7: E2E compra→recepción→inventario |
| **X** | D-IA14: Sugerencia de precios + D-IA16: Dashboard métricas IA |
| **J-V** | B14: Implementar WhatsApp (Twilio) y Slack notifiers reales |

#### Semana 8: Módulos sectoriales
| Día | Tarea |
|-----|-------|
| **L-X** | B8: Módulo mesas/comandas restaurante (base) |
| **J-V** | B9: Variantes de producto (inicio) |

#### Semana 9: Enterprise features
| Día | Tarea |
|-----|-------|
| **L-M** | B11: MFA (TOTP + recovery codes) |
| **X-V** | B10: Multi-moneda con conversión (inicio) |

#### Semana 10: Documentación y onboarding
| Día | Tarea |
|-----|-------|
| **L-M** | B12: Onboarding wizard completo |
| **X-V** | B13: Documentación API enriquecida |

---

## 5. DETALLE TÉCNICO POR TAREA

### A1: Refactorizar `receipts.py` checkout

**Problema:** 800+ líneas de SQL raw en un HTTP handler. Imposible testear unitariamente.

**Solución:** Extraer a `CheckoutService`:

```
pos/
├── application/
│   ├── use_cases.py          ← Ya existe (stubs → implementar)
│   ├── checkout_service.py   ← NUEVO: lógica de negocio
│   └── shift_service.py      ← NUEVO: lógica de turnos
├── domain/
│   ├── receipt.py             ← Entidad de dominio
│   └── shift.py               ← Entidad de dominio
├── infrastructure/
│   └── pos_repository.py      ← Queries SQL
└── interface/
    └── http/
        ├── receipts.py        ← Solo orquesta, llama a servicios
        └── shifts.py          ← Solo orquesta
```

**Patrón:**
```python
# checkout_service.py
class CheckoutService:
    def __init__(self, db: Session, costing_service: InventoryCostingService):
        self.db = db
        self.costing = costing_service

    def execute(self, receipt_id: UUID, payments: list, warehouse_id: UUID) -> CheckoutResult:
        with self.db.begin_nested():  # SAVEPOINT
            receipt = self._get_receipt(receipt_id)
            self._validate_payments(receipt, payments)
            cogs = self._deduct_stock(receipt, warehouse_id)
            self._record_payments(receipt, payments)
            self._create_journal_entry(receipt, cogs)
            receipt.status = "paid"
            return CheckoutResult(...)
```

### B1: Concepto de Sucursal (Branch)

**Migración SQL:**
```sql
CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    address TEXT,
    city VARCHAR(100),
    phone VARCHAR(20),
    is_main BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Vincular tablas existentes
ALTER TABLE warehouses ADD COLUMN branch_id UUID REFERENCES branches(id);
ALTER TABLE pos_registers ADD COLUMN branch_id UUID REFERENCES branches(id);
ALTER TABLE pos_shifts ADD COLUMN branch_id UUID REFERENCES branches(id);
ALTER TABLE company_user_roles ADD COLUMN branch_id UUID REFERENCES branches(id);

-- RLS
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
CREATE POLICY branches_tenant ON branches
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### B2: Billing/Suscripciones Backend

**Modelos:**
```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,          -- 'starter', 'professional', 'enterprise'
    price_monthly NUMERIC(10,2) NOT NULL,
    price_yearly NUMERIC(10,2),
    max_users INT DEFAULT 1,
    max_branches INT DEFAULT 1,
    included_modules TEXT[] DEFAULT '{}',  -- {'products','pos','inventory'}
    features JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    stripe_price_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    status VARCHAR(20) DEFAULT 'active',   -- active, past_due, canceled, trialing
    billing_cycle VARCHAR(10) DEFAULT 'monthly',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### D-IA2: CopilotContextBuilder

```python
# copilot/context_builder.py
class CopilotContextBuilder:
    LOADERS = {
        "pos": "_pos", "inventory": "_inventory", "inventario": "_inventory",
        "purchases": "_purchases", "compras": "_purchases",
        "sales": "_sales", "ventas": "_sales",
        "finances": "_finances", "finanzas": "_finances",
        "productions": "_productions", "produccion": "_productions",
        "expenses": "_expenses", "gastos": "_expenses",
        "hr": "_hr", "rrhh": "_hr",
    }

    @classmethod
    async def build(cls, db: Session, tenant_id: str, module: str | None) -> str:
        method_name = cls.LOADERS.get(module, "_general")
        loader = getattr(cls, method_name)
        raw = loader(db, tenant_id)
        # Aplicar PII masking a todo
        if isinstance(raw, list):
            raw = [pii_mask_row(r) for r in raw]
        return json.dumps(raw, default=str, ensure_ascii=False)

    @staticmethod
    def _pos(db, tid) -> dict:
        # 1. Turno activo
        shift = db.execute(text(
            "SELECT id, status, opened_at, opening_float FROM pos_shifts "
            "WHERE tenant_id = :tid AND status = 'open' ORDER BY opened_at DESC LIMIT 1"
        ), {"tid": tid}).fetchone()
        # 2. Ventas del día
        sales = db.execute(text(
            "SELECT count(*) AS recibos, coalesce(sum(gross_total),0) AS total "
            "FROM pos_receipts WHERE tenant_id = :tid AND created_at::date = CURRENT_DATE"
        ), {"tid": tid}).fetchone()
        # 3. Top 5 productos hoy
        top = db.execute(text(
            "SELECT p.name, sum(rl.qty) AS qty, sum(rl.line_total) AS total "
            "FROM pos_receipt_lines rl JOIN products p ON p.id = rl.product_id "
            "JOIN pos_receipts r ON r.id = rl.receipt_id "
            "WHERE r.tenant_id = :tid AND r.created_at::date = CURRENT_DATE "
            "GROUP BY p.name ORDER BY total DESC LIMIT 5"
        ), {"tid": tid}).fetchall()
        return {
            "turno_activo": dict(shift._mapping) if shift else None,
            "ventas_hoy": dict(sales._mapping) if sales else {},
            "top_productos_hoy": [dict(r._mapping) for r in top],
        }

    @staticmethod
    def _inventory(db, tid) -> dict:
        # Stock bajo, productos sin movimiento 30d, valor total
        ...

    @staticmethod
    def _purchases(db, tid) -> dict:
        # POs pendientes, proveedores activos, última recepción
        ...
```

### D-IA10: Streaming SSE

**Backend:**
```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def ai_chat_stream(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
    async def generate():
        # ... build prompt con CopilotContextBuilder ...
        async for chunk in ai_provider.stream(request):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Frontend:**
```tsx
const eventSource = new EventSource('/api/v1/tenant/ai/chat/stream')
eventSource.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.done) { eventSource.close(); return }
  setMessages(prev => /* append chunk to last assistant message */)
}
```

---

## 6. MÓDULOS COMERCIALES Y SECTORES

### 6.1 Módulos Base (siempre incluidos, no se cobran)
- Auth/Identity
- Tenant/Multitenant
- Modules Catalog
- Settings
- Feature Flags

### 6.2 Paquetes por Sector

| Sector | Paquete Starter | Paquete Pro | Paquete Enterprise |
|--------|----------------|-------------|-------------------|
| 🥖 Panadería | Productos + POS + Inventario | + Producción + Compras + Reportes | + Contabilidad + RRHH + IA |
| 🏪 Retail | Productos + POS + Inventario + Clientes | + Compras + Ventas + Reportes | + E-invoicing + CRM + IA |
| 🍽️ Restaurante | Productos + POS + Inventario + Mesas* | + Producción + Compras + Reportes | + Contabilidad + RRHH + IA |
| 🔧 Ferretería | Productos + POS + Inventario + Clientes | + Compras + Ventas + Variantes* | + E-invoicing + Reportes + IA |
| 💊 Farmacia | Productos + POS + Inventario (lotes) + Clientes | + Compras + Alertas caducidad* | + E-invoicing + Reportes + IA |
| 🏪 Minimarket | Productos + POS + Inventario | + Compras + Gastos + Reportes | + Contabilidad + IA |

*Requiere features marcados con B8, B9, B4 en el inventario de tareas.

### 6.3 Dependencias de Módulos (para validación en Module Catalog)

```
POS              → Productos + Inventario
Ventas           → Productos + Clientes
Compras          → Productos + Proveedores + Inventario
Producción       → Productos + Inventario
Contabilidad     → Finanzas
E-invoicing      → Ventas O POS + Certificados
CRM              → Clientes
Reportes         → Al menos 1 módulo operativo
Impresión        → POS O Ventas
Webhooks         → Al menos 1 módulo emisor
Mesas/Comandas*  → POS
Variantes*       → Productos
```

---

## 7. MÉTRICAS DE ÉXITO

### Fin Semana 3 (Meta: 85%)
- [ ] `receipts.py` checkout refactorizado a `CheckoutService` con < 50 líneas por método
- [ ] Use Cases POS/Inventario implementados (no stubs)
- [ ] Pipeline `close_shift` → journal entries automático
- [ ] 10+ tests nuevos para POS checkout, receive_purchase, auth flow
- [ ] Copilot con `current_module` + CopilotContextBuilder + 11 topics
- [ ] Rate limit por tenant para `/ai/*`
- [ ] Template ticket 80mm funcional
- [ ] `ensure_tenant` logs en debug, `datetime.utcnow()` migrado

### Fin Semana 6 (Meta: 90%)
- [ ] Streaming SSE funcionando en copilot
- [ ] Historial de chat persistido en BD
- [ ] Predicción de reorden + anomalías de ventas funcionando
- [ ] Resumen ejecutivo diario enviándose por email
- [ ] Branch/Sucursal modelo completo con CRUD + vinculación
- [ ] Billing/Suscripciones backend con Stripe recurring
- [ ] Alertas de caducidad funcionando
- [ ] E2E tests POS + compras pasando

### Fin Semana 10 (Meta: 95%)
- [ ] MFA implementado
- [ ] Módulo mesas/comandas base
- [ ] Variantes de producto base
- [ ] Multi-moneda inicio
- [ ] Onboarding wizard completo
- [ ] Documentación API publicada
- [ ] WhatsApp/Slack notifiers reales
- [ ] Dashboard métricas IA
- [ ] User feedback en copilot

### KPIs de Calidad
| Métrica | Actual | Meta S3 | Meta S6 | Meta S10 |
|---------|--------|---------|---------|----------|
| Cobertura tests (archivos) | 70+ | 85+ | 100+ | 120+ |
| Líneas máx por función handler | 800+ | < 50 | < 50 | < 50 |
| Topics copilot | 6 | 11 | 14 | 18 |
| Contexto IA por módulo | 0 | 7 | 10 | 12 |
| Tiempo respuesta chat IA | 2-5s (sin feedback) | 2-5s | < 1s (streaming) | < 1s |
| Rate limit IA | Global | Por tenant | Por tenant | Por tenant + plan |
| Módulos vendibles con billing | 0 | 0 | 15+ | 18+ |

---

## RESUMEN EJECUTIVO

| Fase | Semanas | Tareas | Resultado |
|------|---------|--------|-----------|
| **Fase 1: Fundamentos** | 1-3 | 20 tareas (A1-A8 + C-T1-T4 + D-IA1-IA8 + B3,B5-B7) | Sistema sólido: código limpio, tests, copilot contextual, rate limit |
| **Fase 2: Crecimiento** | 4-6 | 14 tareas (D-IA9-IA16 + B1,B2,B4 + C-T5-T7) | Diferencial: streaming IA, sucursales, billing, alertas |
| **Fase 3: Completitud** | 7-10 | 8 tareas (B8-B14) | Enterprise: MFA, mesas, variantes, multi-moneda, docs |

**Total: 42 tareas en 10 semanas para ir de 78% → 95%+**

---

## 8. ESTADO DE IMPLEMENTACIÓN (Auditoría 17-Mar-2026)

> **Última verificación:** 17 Marzo 2026
> **Método:** Revisión directa del código fuente (backend + frontend + tests + e2e)

### 8.1 BLOQUE A: Calidad de Código (Refactoring)

| Task | Descripción | Estado | Evidencia |
|------|------------|--------|-----------|
| **A1** | Refactorizar `receipts.py` checkout → `CheckoutService` | ✅ IMPLEMENTADO | `pos/application/checkout_service.py` existe con clase `CheckoutService` (L65-117), orquesta pagos y stock |
| **A2** | Use Cases POS reales (no stubs) | ✅ IMPLEMENTADO | `pos/application/use_cases.py` tiene `OpenShiftUseCase` (L29-96), `CheckoutReceiptUseCase` (L158-230) con SQL real e inyección de repositorios |
| **A3** | Use Cases Inventario reales (no stubs) | ✅ IMPLEMENTADO | `inventory/application/use_cases.py` tiene `ReceiveStockUseCase` (L96-215), `TransferStockUseCase` (L302-419) con stock_items y stock_moves reales |
| **A4** | Pipeline automático close_shift → journal entries | ✅ IMPLEMENTADO | `pos/interface/http/shifts.py` (L560-644) genera asientos contables automáticamente al cerrar turno con `JournalEntry` + `JournalEntryLine` |
| **A5** | Migrar `datetime.utcnow()` → `datetime.now(UTC)` | ⚠️ PARCIAL | Backend principal usa `datetime.now(UTC)`. Quedan ~10 usos de `utcnow()` solo en tests (`test_production.py`, `test_pos_backfill_tenant_isolation.py`, `test_margins_analytics_pg.py`) y documentación markdown |
| **A6** | `logger.info` → `logger.debug` en `ensure_tenant` | ✅ IMPLEMENTADO | `middleware/tenant.py:54,60,72,80` todos usan `logger.debug` |
| **A7** | Unificar `_get_system_prompt` en `base.py` | ✅ IMPLEMENTADO | `_get_system_prompt` definido en `services/ai/base.py:141`, `openai.py:64` y `ovhcloud.py:72` lo heredan vía `self._get_system_prompt()` — sin duplicación |
| **A8** | Fix `create_invoice_draft` UUID — quitar `int()` | ✅ IMPLEMENTADO | `copilot/services.py:262` usa `tenant_empresa_id: str` directamente, sin `int()` |

### 8.2 BLOQUE B: Funcionalidad Faltante

| Task | Descripción | Estado Backend | Estado Frontend | Evidencia |
|------|------------|---------------|----------------|-----------|
| **B1** | Sucursal (Branch): modelo + CRUD + migración | ✅ IMPLEMENTADO | ❌ NO IMPL. (sin selector sucursal en frontend) | Backend: `modules/branches/models.py` (Branch con tenant_id, name, code, is_main, etc.) + `interface/http/tenant.py` con CRUD completo (list, create, update, delete, asignar warehouses). Frontend: No existe componente de selector de sucursal |
| **B2** | Billing/suscripciones backend + Stripe recurring | ✅ IMPLEMENTADO | ⚠️ PARCIAL | Backend: `modules/billing/models.py` (SubscriptionPlan + TenantSubscription) + `interface/http/tenant.py` con list plans, get subscription, subscribe, change-plan, cancel + Stripe webhook. Frontend: `modules/billing/` existe con List.tsx, Form.tsx, InvoiceE.tsx — pero es facturación a clientes, no gestión de planes/suscripciones del tenant |
| **B3** | Template ticket POS 80mm térmico | ✅ IMPLEMENTADO | — | `modules/printing/templates/receipt_80mm.py` (302 líneas) con `ReceiptLine`, `ReceiptData`, formateo 48 cols, ESC/POS |
| **B4** | Alertas de caducidad inventario | ❌ NO IMPL. | ❌ NO IMPL. | No existe lógica de expiración/lotes/caducidad en inventario |
| **B5** | Rate limit por tenant (no global) | ✅ IMPLEMENTADO | — | `middleware/rate_limit.py` (global) + `middleware/endpoint_rate_limit.py` (por endpoint con IP) + rate limit por tenant para IA en `copilot/interface/http/tenant.py:67-87` |
| **B6** | Backup automatizado (pg_dump + Celery) | ❌ NO IMPL. | — | Solo documentación/instrucciones manuales en `ops/README.md`. No hay script automatizado ni tarea Celery |
| **B7** | Log rotation | ✅ IMPLEMENTADO | — | `main.py:150-165` usa `RotatingFileHandler` con tamaño máximo y backup count |
| **B8** | Módulo mesas/comandas restaurante | ❌ NO IMPL. | ❌ NO IMPL. | No existe módulo `restaurant/` ni en backend ni en frontend |
| **B9** | Variantes de producto (talla/color) | ❌ NO IMPL. | ❌ NO IMPL. | No hay modelos de variantes en `modules/products/` |
| **B10** | Multi-moneda con conversión real | ❌ NO IMPL. | ❌ NO IMPL. | No existe lógica de exchange_rate ni multi-currency en `modules/finance/` |
| **B11** | MFA (TOTP + recovery codes) | ❌ NO IMPL. | ❌ NO IMPL. | `identity/README.md` explícitamente dice "No cubre: MFA" |
| **B12** | Onboarding wizard completo | ✅ IMPLEMENTADO | ✅ IMPLEMENTADO | Backend: `modules/onboarding/` existe. Frontend: `pages/Onboarding.tsx` (544 líneas) con wizard de 4 pasos (info, regional, branding, review), soporte multi-sector (panadería, restaurante, retail, ferretería, farmacia, minimarket) |
| **B13** | Documentación API enriquecida | ⚠️ PARCIAL | — | Existe `static/docs/redoc.standalone.js` (ReDoc). Documentación auto-generada por FastAPI/OpenAPI, pero sin ejemplos enriquecidos manuales |
| **B14** | WhatsApp y Slack notifiers reales | ❌ STUBS | — | `ai_agent/notifier.py:157` retorna `"status": "sent (mock)"` para WhatsApp, `"status": "sent (stub)"` para Slack |

### 8.3 BLOQUE C: Tests

| Task | Descripción | Estado | Evidencia |
|------|------------|--------|-----------|
| **C-T1** | Tests unitarios POS checkout | ✅ IMPLEMENTADO | `tests/test_pos_checkout.py` existe |
| **C-T2** | Tests receive_purchase con costeo | ✅ IMPLEMENTADO | `tests/test_receive_purchase.py` existe |
| **C-T3** | Tests flujo auth (login→token→refresh→logout) | ✅ IMPLEMENTADO | `tests/test_auth_flow.py` + `test_auth_cookies.py` + `test_login.py` |
| **C-T4** | Tests cierre turno → contabilidad | ✅ IMPLEMENTADO | `tests/test_shift_accounting.py` existe |
| **C-T5** | Tests copilot contextual | ❌ NO IMPL. | No existe test específico para CopilotContextBuilder |
| **C-T6** | E2E Playwright: POS checkout | ✅ IMPLEMENTADO | `e2e/pos.spec.ts` existe |
| **C-T7** | E2E: compra → recepción → inventario | ❌ NO IMPL. | No existe `e2e/purchase_flow.spec.ts` (sí hay `e2e/inventory.spec.ts`) |

### 8.4 BLOQUE D: Integración IA

| Task | Descripción | Estado Backend | Estado Frontend | Evidencia |
|------|------------|---------------|----------------|-----------|
| **D-IA1** | `current_module` en ChatIn + frontend | ✅ IMPLEMENTADO | ✅ IMPLEMENTADO | Backend: `ChatIn.current_module` en `tenant.py:210`. Frontend: `CopilotChatWidget.tsx:91-102` detecta módulo por URL y envía `current_module` |
| **D-IA2** | `CopilotContextBuilder` con loaders por módulo | ✅ IMPLEMENTADO | — | `copilot/context_builder.py` con loaders: POS, Inventario, Compras, Ventas, Finanzas, Producción, Gastos, RRHH, Productos, General (10 loaders) |
| **D-IA3** | Topics nuevos: pos_hoy, gastos_mes, etc. | ✅ IMPLEMENTADO | — | `copilot/services.py` tiene: ventas_mes, ventas_por_almacen, top_productos, stock_bajo, pendientes_sri_sii, cobros_pagos, **pos_hoy** (L185), **gastos_mes** (L193), **produccion_activa** (L202), **compras_pendientes** (L210), **prediccion_reorden** (L218), **anomalias_ventas** (L236) = **12 topics** |
| **D-IA4** | Datos tenant en system prompt (sector, país, moneda) | ✅ IMPLEMENTADO | — | `tenant.py:236-256` consulta `tenants.name, sector, country, currency` y lo incluye en el prompt |
| **D-IA5** | `pii_mask_row()` en todo contexto IA | ✅ IMPLEMENTADO | — | `context_builder.py:57-61` aplica `pii_mask_row` a todos los datos list/dict del contexto |
| **D-IA6** | Rate limit por tenant para `/ai/*` | ✅ IMPLEMENTADO | — | `tenant.py:60-87` implementa rate limit in-memory por tenant (20 req/min chat, 5/min suggestions) |
| **D-IA7** | Predicción de reorden | ✅ IMPLEMENTADO | — | `copilot/services.py:218-234` topic `prediccion_reorden` con consumo/día + stock actual |
| **D-IA8** | Detección anomalías ventas | ✅ IMPLEMENTADO | — | `copilot/services.py:236-255` topic `anomalias_ventas` detecta días < 60% del promedio 30d |
| **D-IA9** | Resumen ejecutivo diario (Celery) | ✅ IMPLEMENTADO | — | `workers/ai_tasks.py:184-242` tarea `daily_executive_summary` + configurada en `celery_config.py:130` |
| **D-IA10** | Streaming SSE `/ai/chat/stream` | ✅ IMPLEMENTADO | ✅ IMPLEMENTADO | Backend: `tenant.py:482` con `StreamingResponse` + `text/event-stream`. Frontend: `CopilotChatWidget.tsx:14-55` con `fetch` + `ReadableStream` + parseo SSE |
| **D-IA11** | Historial chat persistido en BD | ✅ IMPLEMENTADO | ⚠️ PARCIAL | Backend: `copilot/models.py` con `CopilotConversation` + `CopilotMessage` + endpoints CRUD (`/conversations`, `/conversations/:id/messages`, DELETE). Frontend: chat envía/recibe pero no tiene UI para ver historial de conversaciones anteriores |
| **D-IA12** | Sugerencias contextuales por módulo | ✅ IMPLEMENTADO | ✅ IMPLEMENTADO | `CopilotChatWidget.tsx:75-83` tiene `moduleSuggestions` con 7 módulos (POS, inventory, purchases, sales, productions, expenses, finances) |
| **D-IA13** | Clasificación automática gastos | ❌ NO IMPL. | ❌ NO IMPL. | No existe lógica de clasificación automática de gastos vía IA |
| **D-IA14** | Sugerencia de precios basada en recetas | ❌ NO IMPL. | ❌ NO IMPL. | No existe endpoint ni lógica de sugerencia de precios |
| **D-IA15** | User feedback (👍👎) en chat | ✅ IMPLEMENTADO | ✅ IMPLEMENTADO | Backend: `tenant.py:578-610` endpoint `/feedback` con thumbs_up/thumbs_down. Frontend: `CopilotChatWidget.tsx:185-191,329-342` botones feedback con iconos |
| **D-IA16** | Dashboard métricas IA | ❌ NO IMPL. | ❌ NO IMPL. | No existe endpoint ni frontend para métricas IA (requests/día, costo, error rate) |

### 8.5 Estado de Módulos Frontend (Tenant App)

| Módulo | Estado | Archivos/Componentes | Notas |
|--------|--------|---------------------|-------|
| **POS** | ✅ Completo | POSView, components/, hooks/, services, offline sync | Checkout, turnos, recibos |
| **Productos** | ✅ Completo | Dentro de `modules/products/` | CRUD completo |
| **Inventario** | ✅ Completo | Panel, StockList, MovementForm, MovementFormBulk, components/, services/ | Stock, movimientos, ajustes |
| **Compras** | ✅ Completo | List, Form, Detail, components/ | CRUD + recepción |
| **Ventas** | ✅ Completo | List, Form, Detail, components/ | CRUD + tests |
| **Gastos** | ✅ Completo | List, Form, Detail, Panel, components/ | CRUD completo |
| **Producción** | ✅ Completo | Recetas (CRUD), Órdenes, Planner, Calculadora, CostDrivers, Ingredientes | 21 archivos |
| **Contabilidad** | ✅ Completo | ChartOfAccounts (CRUD), JournalEntries (CRUD), Panel, components/, hooks/ | Plan de cuentas + asientos |
| **RRHH** | ✅ Completo | Employees (CRUD), Nóminas, Fichajes, Vacaciones, MiJornada | 21 archivos |
| **Finanzas** | ✅ Completo | Bancos, Cajas, Balances, CashForm, CloseCashModal | Tesorería |
| **Reportes** | ✅ Completo | Dashboard, Financial, Inventory, Sales, Margins, RealProfit | 6 reportes |
| **Facturación/Billing** | ✅ Completo | List, Form, InvoiceE, components/, sectores/ | Facturación a clientes |
| **CRM** | ✅ Completo | components/, pages/, services, types | Pipeline CRM |
| **E-invoicing** | ⚠️ Parcial | EInvoicingDashboard, services | Solo dashboard — falta flujo completo |
| **Copilot IA** | ✅ Completo | Dashboard, Routes, services + CopilotChatWidget (global) | Chat, streaming, feedback |
| **Importador** | ✅ Completo | Panel, components/, pages/, services (SSE) | OCR + importación |
| **Notificaciones** | ⚠️ Parcial | NotificationCenter, services | Centro de notificaciones básico |
| **Webhooks** | ⚠️ Parcial | SubscriptionsList, services | Lista de suscripciones |
| **Reconciliación** | ✅ Completo | Dashboard, ImportForm, StatementDetail | Conciliación bancaria |
| **Configuración** | ✅ Completo | General, Fiscal, Branding, Horarios, Operativo, Notificaciones, Avanzado, Módulos, Límites | 18 archivos |
| **Templates** | ⚠️ Parcial | ConfigViewer, services | Solo visor |
| **Usuarios** | ✅ Completo | Dentro de `modules/users/` | Gestión de usuarios |
| **Clientes** | ✅ Completo | Dentro de `modules/customers/` | CRUD clientes |
| **Proveedores** | ✅ Completo | Dentro de `modules/suppliers/` | CRUD proveedores |
| **Onboarding** | ✅ Completo | `pages/Onboarding.tsx` (544 líneas) | Wizard 4 pasos, multi-sector |

### 8.6 E2E Tests (Playwright)

| Archivo | Estado |
|---------|--------|
| `e2e/auth.spec.ts` | ✅ |
| `e2e/dashboard.spec.ts` | ✅ |
| `e2e/pos.spec.ts` | ✅ |
| `e2e/inventory.spec.ts` | ✅ |
| `e2e/invoicing.spec.ts` | ✅ |
| `e2e/production.spec.ts` | ✅ |
| `e2e/reports.spec.ts` | ✅ |
| `e2e/navigation.spec.ts` | ✅ |
| `e2e/notifications.spec.ts` | ✅ |
| `e2e/reconciliation.spec.ts` | ✅ |
| `e2e/webhooks.spec.ts` | ✅ |
| `e2e/performance.spec.ts` | ✅ |
| `e2e/responsive.spec.ts` | ✅ |
| `e2e/smoke.spec.ts` | ✅ |

### 8.7 Resumen Cuantitativo (Actualizado 17-Mar-2026 post-implementación)

| Métrica | Planificado | Implementado | % |
|---------|-------------|-------------|---|
| **Bloque A** (Refactoring) | 8 tareas | 8 (A5 parcial en tests) | **~97%** |
| **Bloque B** (Features) | 14 tareas | 13 completas + 1 parcial | **~96%** |
| **Bloque C** (Tests) | 7 tareas | 5 completas | **~71%** |
| **Bloque D** (IA) | 16 tareas | 16 completas | **~100%** |
| **TOTAL** | **45 items** | **42 completas + 2 parciales** | **~96%** |

### 8.8 Implementaciones realizadas en esta sesión (17-Mar-2026)

#### ✅ Backend implementado
| Task | Descripción | Archivos creados |
|------|------------|-----------------|
| B4 | Alertas de caducidad inventario | `inventory/application/expiry_alerts.py`, `inventory/interface/http/expiry.py`, `workers/expiry_tasks.py` |
| B6 | Backup automatizado | `ops/scripts/backup.sh`, `workers/backup_tasks.py` + config Celery |
| B8 | Módulo mesas/comandas restaurante | `restaurant/models.py`, `restaurant/interface/http/tenant.py` (11 endpoints) |
| B9 | Variantes de producto | `products/domain/variants.py`, `products/interface/http/variants.py` (6 endpoints) |
| B10 | Multi-moneda con conversión | `finance/application/multicurrency.py`, `finance/interface/http/multicurrency.py` (4 endpoints) |
| B11 | MFA (TOTP + recovery codes) | `identity/application/mfa.py`, `identity/interface/http/mfa.py` (5 endpoints) |
| B14 | WhatsApp (Twilio) y Slack reales | `ai_agent/notifier.py` actualizado — Twilio API + Slack Bot Token API |
| D-IA13 | Clasificación automática gastos | `POST /ai/classify-expense` + topic en `copilot/services.py` |
| D-IA14 | Sugerencia de precios | `POST /ai/suggest-price` con cálculo receta + IA |
| D-IA16 | Dashboard métricas IA | `GET /ai/metrics` con requests/día, costo, error rate |

#### ✅ Frontend implementado
| Task | Descripción | Archivos creados |
|------|------------|-----------------|
| B1 frontend | Selector de sucursal + gestión | `components/BranchSelector.tsx`, `settings/BranchesManager.tsx` |
| B2 frontend | Página planes/suscripción | `settings/SubscriptionManager.tsx` |
| B8 frontend | Módulo restaurante completo | `restaurant/TablesView.tsx`, `restaurant/OrderView.tsx`, `restaurant/services.ts`, `restaurant/Routes.tsx` |
| D-IA11 frontend | UI historial conversaciones copilot | `CopilotChatWidget.tsx` actualizado con panel de historial |

### 8.9 Normalización de IDs internos a inglés canónico (2026-03-18)

Se completó la migración de todos los identificadores legacy en español a sus equivalentes canónicos en inglés. Esto afecta **manifests**, **permission keys**, **i18n namespaces**, **plantillas/services**, **backend permission guards** y **tests**.

#### Mapeo de IDs aplicado

| Legacy (ES) | Canónico (EN) | Capas afectadas |
|-------------|---------------|-----------------|
| `usuarios` | `users` | manifest id, permission keys, backend guards, locale keys, tests |
| `produccion` | `production` | manifest id/name/permissions, API field queries, locale keys |
| `facturacion` | `billing` | manifest permissions, locale keys |
| `clientes` | `customers` | manifest name/permissions, API field queries, navigation |
| `finanzas` | `finances` | manifest permissions |
| `rrhh` | `hr` | manifest permissions |
| `reportes` | `reports` | manifest id/name, i18n namespace rename, translation keys |
| `inventarioManifest` | `inventoryManifest` | export name, index imports |
| `contabilidadManifest` | `accountingManifest` | export name |
| `productosManifest` | `productsManifest` | export name, index imports |
| `Configuracion` | `Settings` | manifest name/menu title |
| `ventas` (nav/sector) | `sales` | navigation service, sector configs, quick actions |

#### Archivos modificados (~35 files)

**Manifests** (10): users, productions, billing, customers, inventory, accounting, reports, settings, hr, finances, products, crm, index.ts

**Permission keys** (7): locales/es/permissions.json, locales/en/permissions.json, backend permissions.py, Routes.tsx, ProtectedRoute.tsx, ProtectedButton.tsx, tests

**i18n** (3): i18n/index.ts, locales/en/reportes.json → reports.json, locales/es/reportes.json → reports.json

**Plantillas/navigation** (3): navigationService.ts, dashboard.ts, taller_pro.tsx, DashboardPro.tsx

**Reports** (6): ReportsDashboard, SalesReport, InventoryReport, FinancialReport, RealProfitReport, MarginsDashboard

**Settings** (2): ModulosPanel.tsx, SubscriptionManager.test.tsx

**Forms** (2): customers/Form.tsx, productions/OrderForm.tsx

**Tests** (5): manifests.test.ts, index.test.ts, manifest.test.ts, ProtectedButton.test.tsx, ProtectedRoute.test.tsx, usePermission.test.ts

**Migration** (1): `2026-03-18_002_normalize_permission_keys_to_english` — normalizes `global_action_permissions` keys and `company_roles.permissions` JSONB

### 8.10 Tareas Pendientes (solo tests y docs — código completado)

| Task | Descripción | Tipo |
|------|------------|------|
| A5 (parcial) | `datetime.utcnow()` en archivos de test | Tests |
| C-T5 | Tests copilot contextual | Tests |
| C-T7 | E2E compra → recepción → inventario | Tests |
| B13 | Documentación API enriquecida con ejemplos | Documentación |
