# 📋 PLAN DE ACCIÓN INMEDIATO - GESTIQCLOUD

**Fecha:** Noviembre 2025  
**Versión:** 2.0.0  
**Objetivo:** Completar MVP en 2-3 semanas

---

## 🎯 PRIORIDADES CRÍTICAS

### SEMANA 1: E-Facturación + Pagos Online

#### Tarea 1.1: Endpoints REST E-Facturación (2 días)
**Estado:** 95% workers listos, falta REST API

**Archivos a crear/modificar:**
```
apps/backend/app/routers/einvoicing.py  (CREAR - 300 líneas)
├── POST /api/v1/einvoicing/send
├── GET /api/v1/einvoicing/status/{invoice_id}
├── GET /api/v1/einvoicing/submissions
└── POST /api/v1/einvoicing/retry/{submission_id}
```

**Código base:**
```python
# apps/backend/app/routers/einvoicing.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

router = APIRouter(prefix="/api/v1/einvoicing", tags=["einvoicing"])

@router.post("/send")
async def send_einvoice(
    invoice_id: UUID,
    country: str = "EC",  # EC o ES
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id)
):
    """
    Enviar factura a SRI (Ecuador) o AEAT (España)
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == tenant_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if country == "EC":
        # Trigger Celery task
        from app.workers.einvoicing_tasks import sign_and_send_sri_task
        sign_and_send_sri_task.delay(str(invoice_id))
    elif country == "ES":
        from app.workers.einvoicing_tasks import sign_and_send_facturae_task
        sign_and_send_facturae_task.delay(str(invoice_id))
    
    return {"status": "processing", "invoice_id": invoice_id}

@router.get("/status/{invoice_id}")
async def get_einvoice_status(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id)
):
    """
    Obtener estado de factura electrónica
    """
    submission = db.query(SriSubmission).filter(
        SriSubmission.invoice_id == invoice_id,
        SriSubmission.tenant_id == tenant_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {
        "invoice_id": invoice_id,
        "status": submission.status,
        "clave_acceso": submission.clave_acceso,
        "error_message": submission.error_message,
        "submitted_at": submission.submitted_at
    }
```

**Checklist:**
- [ ] Crear router einvoicing.py
- [ ] Implementar 4 endpoints
- [ ] Agregar schemas Pydantic
- [ ] Montar router en main.py
- [ ] Testing con curl
- [ ] Documentación OpenAPI

**Tiempo estimado:** 2 días

---

#### Tarea 1.2: Frontend Módulo Facturación (3 días)
**Estado:** Backend listo, falta UI

**Archivos a crear:**
```
apps/tenant/src/modules/facturacion/
├── FacturacionView.tsx          (CREAR - 400 líneas)
├── FacturaList.tsx              (CREAR - 350 líneas)
├── FacturaForm.tsx              (CREAR - 300 líneas)
├── EinvoiceStatus.tsx           (CREAR - 200 líneas)
├── services.ts                  (CREAR - 150 líneas)
├── Routes.tsx                   (CREAR - 50 líneas)
├── manifest.ts                  (CREAR - 30 líneas)
└── README.md                    (CREAR - 200 líneas)
```

**Componente base:**
```typescript
// apps/tenant/src/modules/facturacion/FacturacionView.tsx
import React, { useState, useEffect } from 'react';
import { FacturaList } from './FacturaList';
import { FacturaForm } from './FacturaForm';
import { EinvoiceStatus } from './EinvoiceStatus';

export const FacturacionView: React.FC = () => {
    const [facturas, setFacturas] = useState([]);
    const [selectedFactura, setSelectedFactura] = useState(null);
    const [showForm, setShowForm] = useState(false);

    useEffect(() => {
        loadFacturas();
    }, []);

    const loadFacturas = async () => {
        try {
            const response = await fetch('/api/v1/invoices', {
                headers: { 'X-Tenant-ID': getTenantId() }
            });
            setFacturas(await response.json());
        } catch (error) {
            console.error('Error loading facturas:', error);
        }
    };

    const handleSendEinvoice = async (facturaId: string) => {
        try {
            const response = await fetch('/api/v1/einvoicing/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': getTenantId()
                },
                body: JSON.stringify({
                    invoice_id: facturaId,
                    country: 'EC'  // o 'ES'
                })
            });
            
            if (response.ok) {
                alert('Factura enviada a SRI');
                loadFacturas();
            }
        } catch (error) {
            console.error('Error sending einvoice:', error);
        }
    };

    return (
        <div className="facturacion-container">
            <h1>Facturación</h1>
            
            <div className="controls">
                <button onClick={() => setShowForm(true)}>
                    + Nueva Factura
                </button>
            </div>

            {showForm && (
                <FacturaForm
                    onClose={() => setShowForm(false)}
                    onSave={() => {
                        setShowForm(false);
                        loadFacturas();
                    }}
                />
            )}

            <FacturaList
                facturas={facturas}
                onSelect={setSelectedFactura}
                onSendEinvoice={handleSendEinvoice}
            />

            {selectedFactura && (
                <EinvoiceStatus facturaId={selectedFactura.id} />
            )}
        </div>
    );
};
```

**Checklist:**
- [ ] Crear componentes React
- [ ] Implementar servicios API
- [ ] Agregar estilos CSS
- [ ] Integrar con módulo POS
- [ ] Testing manual
- [ ] Documentación

**Tiempo estimado:** 3 días

---

#### Tarea 1.3: Testing E-Facturación (1 día)
**Estado:** Pendiente

**Archivos a crear:**
```
apps/backend/app/tests/test_einvoicing.py  (CREAR - 200 líneas)
```

**Tests a implementar:**
```python
def test_send_sri_invoice():
    """Test envío a SRI Ecuador"""
    pass

def test_send_facturae_invoice():
    """Test envío a Facturae España"""
    pass

def test_get_einvoice_status():
    """Test obtener estado"""
    pass

def test_retry_failed_submission():
    """Test reintentar envío fallido"""
    pass
```

**Checklist:**
- [ ] Crear test file
- [ ] Implementar 4 tests
- [ ] Ejecutar pytest
- [ ] Cobertura > 80%

**Tiempo estimado:** 1 día

---

### SEMANA 2: Integración Pagos Online + Refinamiento

#### Tarea 2.1: Endpoints Pagos Online (1 día)
**Estado:** Providers 100% listos, falta integración

**Archivos a modificar:**
```
apps/backend/app/routers/payments.py  (ACTUALIZAR - agregar 100 líneas)
```

**Endpoints a completar:**
```python
@router.post("/api/v1/payments/link")
async def create_payment_link(
    invoice_id: UUID,
    provider: str = "stripe",  # stripe, kushki, payphone
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id)
):
    """Crear enlace de pago"""
    invoice = db.query(Invoice).get(invoice_id)
    
    if provider == "stripe":
        from app.services.payments.stripe_provider import StripeProvider
        provider_instance = StripeProvider()
    elif provider == "kushki":
        from app.services.payments.kushki_provider import KushkiProvider
        provider_instance = KushkiProvider()
    elif provider == "payphone":
        from app.services.payments.payphone_provider import PayPhoneProvider
        provider_instance = PayPhoneProvider()
    
    link = provider_instance.create_link(
        amount=invoice.total,
        currency="EUR" if tenant.country == "ES" else "USD"
    )
    
    return {"payment_link": link, "provider": provider}

@router.post("/api/v1/payments/webhook/{provider}")
async def payment_webhook(
    provider: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Webhook de confirmación de pago"""
    if provider == "stripe":
        from app.services.payments.stripe_provider import StripeProvider
        provider_instance = StripeProvider()
    # ... similar para otros providers
    
    if provider_instance.verify_webhook(payload):
        # Actualizar invoice status
        invoice = db.query(Invoice).filter(
            Invoice.id == payload.get("invoice_id")
        ).first()
        invoice.estado = "paid"
        db.commit()
        return {"status": "ok"}
    
    return {"status": "error"}
```

**Checklist:**
- [ ] Completar endpoints
- [ ] Integrar providers
- [ ] Testing con Postman
- [ ] Documentación

**Tiempo estimado:** 1 día

---

#### Tarea 2.2: Frontend Botón Pagar Online (2 días)
**Estado:** Pendiente

**Archivos a crear:**
```
apps/tenant/src/modules/pos/PaymentLinkModal.tsx  (CREAR - 250 líneas)
```

**Componente:**
```typescript
export const PaymentLinkModal: React.FC<{
    invoice: Invoice;
    onClose: () => void;
}> = ({ invoice, onClose }) => {
    const [provider, setProvider] = useState('stripe');
    const [loading, setLoading] = useState(false);
    const [paymentLink, setPaymentLink] = useState(null);

    const handleCreateLink = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/v1/payments/link', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': getTenantId()
                },
                body: JSON.stringify({
                    invoice_id: invoice.id,
                    provider: provider
                })
            });
            
            const data = await response.json();
            setPaymentLink(data.payment_link);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal onClose={onClose}>
            <h2>Pagar Online</h2>
            
            <div>
                <label>Proveedor:</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                    <option value="stripe">Stripe (España)</option>
                    <option value="kushki">Kushki (Ecuador)</option>
                    <option value="payphone">PayPhone (Ecuador)</option>
                </select>
            </div>

            <div>
                <p>Monto: {invoice.total} {invoice.currency}</p>
            </div>

            {paymentLink ? (
                <div>
                    <p>Enlace de pago generado:</p>
                    <a href={paymentLink} target="_blank" rel="noopener noreferrer">
                        {paymentLink}
                    </a>
                    <button onClick={() => window.open(paymentLink)}>
                        Abrir en nueva ventana
                    </button>
                </div>
            ) : (
                <button onClick={handleCreateLink} disabled={loading}>
                    {loading ? 'Generando...' : 'Generar enlace'}
                </button>
            )}
        </Modal>
    );
};
```

**Checklist:**
- [ ] Crear componente
- [ ] Integrar con POS
- [ ] Testing manual
- [ ] Documentación

**Tiempo estimado:** 2 días

---

#### Tarea 2.3: Testing Pagos Online (1 día)
**Estado:** Pendiente

**Tests:**
```python
def test_create_stripe_link():
    """Test crear enlace Stripe"""
    pass

def test_create_kushki_link():
    """Test crear enlace Kushki"""
    pass

def test_payment_webhook_stripe():
    """Test webhook Stripe"""
    pass

def test_payment_webhook_kushki():
    """Test webhook Kushki"""
    pass
```

**Checklist:**
- [ ] Crear tests
- [ ] Ejecutar pytest
- [ ] Cobertura > 80%

**Tiempo estimado:** 1 día

---

### SEMANA 3: Refinamiento + Testing Completo

#### Tarea 3.1: Testing Completo (2 días)
**Estado:** 40% backend, 0% frontend

**Archivos a crear:**
```
apps/backend/app/tests/test_pos_complete.py
apps/backend/app/tests/test_inventory_complete.py
apps/tenant/src/modules/importador/__tests__/
apps/tenant/src/modules/productos/__tests__/
apps/tenant/src/modules/pos/__tests__/
```

**Checklist:**
- [ ] Backend: 80% cobertura
- [ ] Frontend: 60% cobertura
- [ ] E2E tests (Cypress)
- [ ] Performance tests

**Tiempo estimado:** 2 días

---

#### Tarea 3.2: Documentación API (1 día)
**Estado:** Swagger disponible, falta completar

**Archivos a actualizar:**
```
apps/backend/app/main.py  (Agregar OpenAPI config)
docs/API_REFERENCE.md     (CREAR - 500 líneas)
```

**Checklist:**
- [ ] Completar docstrings
- [ ] Generar OpenAPI
- [ ] Crear Postman collection
- [ ] Documentar webhooks

**Tiempo estimado:** 1 día

---

#### Tarea 3.3: Optimización Performance (1 día)
**Estado:** Básico implementado

**Tareas:**
- [ ] Agregar índices faltantes
- [ ] Implementar caching Redis
- [ ] Optimizar queries N+1
- [ ] Benchmarking

**Checklist:**
- [ ] Latencia P95 < 300ms
- [ ] Error rate < 0.5%
- [ ] Disponibilidad > 99.5%

**Tiempo estimado:** 1 día

---

## 📊 CRONOGRAMA DETALLADO

```
SEMANA 1 (5 días)
├── Lunes-Martes:   E-Facturación endpoints (2 días)
├── Miércoles-Viernes: Frontend facturación (3 días)
└── Viernes:        Testing e-facturación (1 día)

SEMANA 2 (5 días)
├── Lunes:          Endpoints pagos online (1 día)
├── Martes-Miércoles: Frontend pagos (2 días)
├── Jueves:         Testing pagos (1 día)
└── Viernes:        Refinamiento (1 día)

SEMANA 3 (5 días)
├── Lunes-Martes:   Testing completo (2 días)
├── Miércoles:      Documentación API (1 día)
├── Jueves:         Performance (1 día)
└── Viernes:        QA + Fixes (1 día)
```

---

## 🔧 COMANDOS ÚTILES

### Setup Local
```bash
# Levantar stack completo
docker compose --profile web --profile worker up -d

# Ver logs
docker logs -f backend
docker logs -f celery-worker

# Ejecutar migraciones
docker compose --profile migrate up

# Acceder a DB
docker exec -it db psql -U postgres -d gestiqclouddb_dev
```

### Testing
```bash
# Backend tests
cd apps/backend
pytest app/tests -v --cov=app

# Frontend tests
cd apps/tenant
npm test

# E2E tests
npm run test:e2e
```

### Deployment
```bash
# Build images
docker compose build

# Push to registry
docker tag backend:latest myregistry/backend:latest
docker push myregistry/backend:latest

# Deploy
docker compose -f docker-compose.prod.yml up -d
```

---

## 📋 CHECKLIST FINAL

### Antes de MVP
- [ ] E-facturación: 100% (endpoints + workers)
- [ ] Pagos online: 100% (endpoints + providers)
- [ ] Frontend facturación: 100%
- [ ] Frontend pagos: 100%
- [ ] Testing: 80% backend, 60% frontend
- [ ] Documentación: 100%
- [ ] Performance: Optimizado
- [ ] Seguridad: Auditado

### Antes de Producción
- [ ] SSL/TLS configurado
- [ ] Backups automáticos
- [ ] Monitoreo activo
- [ ] Alertas configuradas
- [ ] Disaster recovery plan
- [ ] Load testing completado
- [ ] Security audit completado
- [ ] Compliance verificado (RGPD, LOPDGDD)

---

## 💡 NOTAS IMPORTANTES

### Dependencias Externas
- **Stripe API:** Requiere API key (test + prod)
- **Kushki API:** Requiere API key (test + prod)
- **PayPhone API:** Requiere API key (test + prod)
- **SRI Ecuador:** Requiere certificado digital (p12)
- **AEAT España:** Requiere certificado digital (p12)

### Configuración Requerida
```bash
# .env
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

KUSHKI_API_KEY=...
KUSHKI_MERCHANT_ID=...

PAYPHONE_API_KEY=...
PAYPHONE_MERCHANT_ID=...

SRI_CERTIFICATE_PATH=/app/uploads/certs/sri.p12
SRI_CERTIFICATE_PASSWORD=...

AEAT_CERTIFICATE_PATH=/app/uploads/certs/aeat.p12
AEAT_CERTIFICATE_PASSWORD=...
```

### Recursos Útiles
- **SRI Ecuador:** https://www.sri.gob.ec/facturacion-electronica
- **AEAT España:** https://www.aeat.es/
- **Stripe Docs:** https://stripe.com/docs
- **Kushki Docs:** https://docs.kushkipagos.com/
- **PayPhone Docs:** https://www.payphone.com.ec/

---

## 🎯 MÉTRICAS DE ÉXITO

### Funcionalidad
- ✅ E-facturación: 100% operativa
- ✅ Pagos online: 100% operativa
- ✅ POS: 100% operativa
- ✅ Inventario: 100% operativo

### Calidad
- ✅ Tests: 80% backend, 60% frontend
- ✅ Documentación: 100%
- ✅ Performance: P95 < 300ms
- ✅ Disponibilidad: > 99.5%

### Seguridad
- ✅ JWT: Implementado
- ✅ RLS: Implementado
- ✅ CORS: Configurado
- ✅ Rate limiting: Implementado

---

## 📞 CONTACTO Y SOPORTE

**Documentación:**
- AGENTS.md - Arquitectura completa
- README_DEV.md - Guía de desarrollo
- ANALISIS_PROYECTO_COMPLETO.md - Este análisis

**Equipo:**
- Backend: Python/FastAPI
- Frontend: React/TypeScript
- DevOps: Docker/PostgreSQL

---

**Plan de acción creado:** Noviembre 2025  
**Versión:** 2.0.0  
**Objetivo:** MVP completo en 2-3 semanas  
**Estado:** 🟢 Listo para implementar
