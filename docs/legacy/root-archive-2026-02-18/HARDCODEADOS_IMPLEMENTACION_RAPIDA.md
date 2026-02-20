# Implementación Rápida - Deshardcodear Configuración

**Objetivo**: Plan accionable para eliminar los hardcodeados más críticos en 1-2 sprints.

---

## 1️⃣ QUICK WIN - Eliminar Fallbacks de API (1 día)

### Problema
```typescript
// apps/tenant/vite.config.ts (línea 11)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';  // ❌ BAD
```

### Solución
```typescript
// apps/tenant/vite.config.ts
const API_URL = import.meta.env.VITE_API_URL;
if (!API_URL) {
    throw new Error('VITE_API_URL env var is required');
}
```

### Variables de Entorno Requeridas
```bash
# .env.development
VITE_API_URL=http://localhost:8000

# .env.production
VITE_API_URL=https://api.gestiqcloud.com
```

---

## 2️⃣ QUICK WIN - Hacer Obligatorias Credenciales (1 día)

### Problema
```python
# apps/backend/app/config/celery_config.py (línea 35)
CELERY_BROKER_URL = getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')  # ❌ BAD
```

### Solución
```python
# apps/backend/app/config/celery_config.py
from pydantic import ValidationError

def get_celery_config():
    broker_url = getenv('CELERY_BROKER_URL')
    if not broker_url:
        raise ValueError('CELERY_BROKER_URL is required. Set in .env')
    return broker_url

CELERY_BROKER_URL = get_celery_config()
```

### .env Obligatorias
```bash
# .env.production.example
DATABASE_URL=postgresql://user:pass@host:5432/db
CELERY_BROKER_URL=redis://redis-host:6379/0
REDIS_URL=redis://redis-host:6379/0
SECRET_KEY=GENERATED-SECURELY
JWT_SECRET_KEY=GENERATED-SECURELY
```

---

## 3️⃣ MEDIUM EFFORT - Extraer DEFAULT_ID_TYPES (2-3 días)

### Paso 1: Backend - Crear API Endpoint

```python
# apps/backend/app/modules/pos/routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1", tags=["pos"])

@router.get("/id-types")
async def get_id_types(db: Session = Depends(get_db), tenant_id: str = Header(...)):
    """Retorna tipos de ID configurados para el tenant"""
    id_types = db.query(IDTypeConfig).filter(
        IDTypeConfig.tenant_id == tenant_id,
        IDTypeConfig.active == True
    ).all()

    return [
        {"code": t.code, "name": t.name, "label": t.label}
        for t in id_types
    ]
```

### Paso 2: Backend - Crear Modelo

```python
# apps/backend/app/models/pos.py
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class IDTypeConfig(Base):
    __tablename__ = "pos_id_type_configs"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    code = Column(String(50), nullable=False)  # CEDULA, RUC, PASSPORT
    name = Column(String(100), nullable=False)
    label = Column(String(100))  # Label para UI
    regex_pattern = Column(String(200))  # Para validación
    active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code'),
    )
```

### Paso 3: Backend - Seed Data

```python
# migrations/add_id_types.sql
INSERT INTO pos_id_type_configs (tenant_id, code, name, label, regex_pattern, active)
VALUES
    ('tenant-123', 'CEDULA', 'Cédula', 'C.I.', '^\d{10}$', true),
    ('tenant-123', 'RUC', 'RUC', 'R.U.C.', '^\d{13}$', true),
    ('tenant-123', 'PASSPORT', 'Pasaporte', 'Pasaporte', '^[A-Z0-9]{6,12}$', true),
    ('tenant-123', 'CEDULA_EXTRANJERA', 'Cédula Extranjera', 'Cédula Ext.', '^\d{10}$', true);
```

### Paso 4: Frontend - Usar API

```typescript
// apps/tenant/src/hooks/usePOS.ts
export function useIDTypes() {
    const { data: idTypes, isLoading } = useSWR(
        '/api/v1/id-types',
        fetcher
    );

    return { idTypes: idTypes || [], isLoading };
}

// apps/tenant/src/modules/pos/POSView.tsx
export default function POSView() {
    const { idTypes } = useIDTypes();  // ✅ Dinámico

    // Usar idTypes en lugar de DEFAULT_ID_TYPES
    const options = idTypes.map(t => ({ value: t.code, label: t.name }));

    return (
        <Select
            options={options}
            placeholder="Seleccione tipo de documento"
        />
    );
}
```

---

## 4️⃣ MEDIUM EFFORT - Payment Methods de BD (3 días)

### Paso 1: Backend - Eliminar Enum

```python
# ANTES - apps/backend/app/models/core/payment.py
class CorePaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    # ... etc

# DESPUÉS - API solo
# (El enum se reemplaza con datos de BD)
```

### Paso 2: Backend - Crear Tabla

```python
# apps/backend/app/models/payments.py
class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    code = Column(String(50), nullable=False)  # cash, card, transfer
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    enabled = Column(Boolean, default=True)
    order = Column(Integer, default=0)  # Para ordenar en UI

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code'),
    )
```

### Paso 3: Backend - API Endpoint

```python
# apps/backend/app/modules/payments/routes.py
@router.get("/payment-methods")
async def get_payment_methods(
    db: Session = Depends(get_db),
    tenant_id: str = Header(...)
):
    """Retorna métodos de pago configurados"""
    methods = db.query(PaymentMethod).filter(
        PaymentMethod.tenant_id == tenant_id,
        PaymentMethod.enabled == True
    ).order_by(PaymentMethod.order).all()

    return [
        {
            "code": m.code,
            "name": m.name,
            "icon": m.icon,
        }
        for m in methods
    ]
```

### Paso 4: Backend - Seed Data

```sql
-- migrations/initialize_payment_methods.sql
INSERT INTO payment_methods (tenant_id, code, name, icon, enabled, "order") VALUES
    ('tenant-123', 'cash', 'Efectivo', 'dollar-sign', true, 1),
    ('tenant-123', 'card', 'Tarjeta', 'credit-card', true, 2),
    ('tenant-123', 'transfer', 'Transferencia', 'arrow-right', true, 3),
    ('tenant-123', 'check', 'Cheque', 'check', true, 4),
    ('tenant-123', 'store_credit', 'Crédito Tienda', 'gift', true, 5);
```

### Paso 5: Frontend - Reemplazar Enum

```typescript
// ANTES
import { CorePaymentMethod } from '../types';
const methods = Object.values(CorePaymentMethod);

// DESPUÉS
const { data: paymentMethods } = useSWR(
    '/api/v1/payment-methods',
    fetcher
);

return (
    <Select
        options={paymentMethods.map(m => ({
            value: m.code,
            label: m.name,
            icon: m.icon
        }))}
    />
);
```

---

## 5️⃣ QUICK WIN - Configuración Global por Tenant (2 días)

### Backend - Crear Tabla

```python
# apps/backend/app/models/configuration.py
class TenantConfiguration(Base):
    __tablename__ = "tenant_configurations"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    key = Column(String(100), nullable=False)  # currency, timezone, tax_rate
    value = Column(Text, nullable=False)
    data_type = Column(String(20), default="string")  # string, number, boolean, json
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'key'),
    )
```

### Backend - API Endpoint

```python
# apps/backend/app/modules/config/routes.py
@router.get("/config")
async def get_config(
    db: Session = Depends(get_db),
    tenant_id: str = Header(...)
):
    """Obtiene configuración completa del tenant"""
    configs = db.query(TenantConfiguration).filter(
        TenantConfiguration.tenant_id == tenant_id
    ).all()

    result = {}
    for c in configs:
        value = c.value
        if c.data_type == "number":
            value = float(value)
        elif c.data_type == "boolean":
            value = value.lower() == "true"
        elif c.data_type == "json":
            value = json.loads(value)

        result[c.key] = value

    return result

@router.post("/config/{key}")
async def set_config(
    key: str,
    value: Any,
    db: Session = Depends(get_db),
    tenant_id: str = Header(...)
):
    """Actualiza una configuración"""
    config = db.query(TenantConfiguration).filter(
        TenantConfiguration.tenant_id == tenant_id,
        TenantConfiguration.key == key
    ).first()

    if not config:
        config = TenantConfiguration(
            tenant_id=tenant_id,
            key=key,
            value=str(value),
            data_type=type(value).__name__
        )
        db.add(config)
    else:
        config.value = str(value)

    db.commit()
    return {"status": "updated"}
```

### Seed Data

```sql
-- migrations/initialize_tenant_config.sql
INSERT INTO tenant_configurations (tenant_id, key, value, data_type) VALUES
    ('tenant-123', 'currency', 'USD', 'string'),
    ('tenant-123', 'timezone', 'America/Guayaquil', 'string'),
    ('tenant-123', 'default_tax_rate', '0.15', 'number'),
    ('tenant-123', 'language', 'es', 'string'),
    ('tenant-123', 'allow_negative_stock', 'false', 'boolean');
```

### Frontend - Usar Configuración

```typescript
// apps/tenant/src/hooks/useConfig.ts
export function useConfig() {
    const { data: config } = useSWR('/api/v1/config', fetcher);

    return {
        currency: config?.currency || 'USD',
        timezone: config?.timezone || 'America/Guayaquil',
        defaultTaxRate: config?.default_tax_rate || 0,
        language: config?.language || 'es'
    };
}

// apps/tenant/src/constants/defaults.ts
// Mantener solo fallbacks seguros para desarrollo
export const SAFE_DEFAULTS = {
    CURRENCY: 'USD',
    TIMEZONE: 'America/Guayaquil',
    DEFAULT_TAX_RATE: 0
};

// En componentes
export function POSView() {
    const config = useConfig();  // ✅ Dinámico

    return <div>Currency: {config.currency}</div>;
}
```

---

## 6️⃣ IMPLEMENTACIÓN - Checklist

### Semana 1 (Quick Wins)
- [ ] Eliminar fallback `http://localhost:8000` en vite.config.ts
- [ ] Hacer obligatorias credenciales en `.env`
- [ ] Validar env vars en startup (Backend)
- [ ] Documentar todas las env vars requeridas

### Semana 2 (Core Tables)
- [ ] Crear tabla `tenant_configurations`
- [ ] Crear tabla `payment_methods`
- [ ] Crear tabla `pos_id_type_configs`
- [ ] Seed data de configuración
- [ ] Crear endpoints GET para cada tabla

### Semana 3 (Frontend Integration)
- [ ] Hooks para consumir configuración
- [ ] Reemplazar imports de enums por API calls
- [ ] Remover arrays hardcodeados en POSView
- [ ] Testing y validación

---

## 🧪 Testing Checklist

```bash
# Backend
pytest apps/backend/tests/test_payment_methods.py
pytest apps/backend/tests/test_config_api.py

# Frontend
npm run test -- POSView.test.tsx
npm run test -- useConfig.test.ts

# Integration
npm run e2e -- pos-payment-selection.spec.ts
```

---

## 📊 Métricas de Éxito

| Métrica | Actual | Target |
|---------|--------|--------|
| Hardcodeados críticos | 8 | 0 |
| Constantes en código | 20+ | <5 (solo safe defaults) |
| Configurables por tenant | 0% | 100% |
| Env vars obligatorias validadas | 50% | 100% |
| Tests para configuración | 0% | 90%+ |
