# Webhooks Integration Guide

Guía para integrar webhooks en otros módulos de GestiqCloud.

## Tabla de Contenidos

1. [Triggering Webhooks](#triggering-webhooks)
2. [Webhook Events](#webhook-events)
3. [Integration Examples](#integration-examples)
4. [Testing Webhooks](#testing-webhooks)

---

## Triggering Webhooks

### Método 1: Directo con SQLAlchemy (Simple)

```python
from sqlalchemy import text
from app.config.database import SessionLocal
from app.modules.webhooks.utils import WebhookFormatter

def create_invoice(invoice_data: dict, tenant_id: str):
    """Create an invoice and trigger webhook"""
    with SessionLocal() as db:
        # Create invoice in database
        invoice = create_invoice_in_db(db, invoice_data, tenant_id)
        
        # Trigger webhook
        payload = WebhookFormatter.format_event_payload(
            event="invoice.created",
            resource_type="invoice",
            resource_id=invoice.id,
            data={
                "invoice_number": invoice.number,
                "amount": str(invoice.total),
                "currency": invoice.currency,
                "customer": invoice.customer_name,
                "status": invoice.status,
            },
            tenant_id=tenant_id,
        )
        
        # Enqueue deliveries
        db.execute(
            text(
                """
                SELECT 1 FROM webhook_subscriptions
                WHERE tenant_id = :tid AND event = :event AND active = true
                """
            ),
            {"tid": tenant_id, "event": "invoice.created"},
        )
        
        if db.execute(...).scalar():
            # Create delivery records
            subs = db.execute(
                text(
                    """
                    SELECT id, url, secret FROM webhook_subscriptions
                    WHERE tenant_id = :tid AND event = :event AND active = true
                    """
                ),
                {"tid": tenant_id, "event": "invoice.created"},
            ).fetchall()
            
            for sub_id, url, secret in subs:
                db.execute(
                    text(
                        """
                        INSERT INTO webhook_deliveries(
                            tenant_id, event, payload, target_url, secret, status
                        )
                        VALUES (:tid, :event, :payload::jsonb, :url, :secret, 'PENDING')
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "event": "invoice.created",
                        "payload": json.dumps(payload),
                        "url": url,
                        "secret": secret,
                    },
                )
        
        db.commit()
        return invoice
```

### Método 2: Service Helper (Recomendado)

```python
from app.modules.webhooks.service import WebhookService

def create_invoice(invoice_data: dict, tenant_id: str):
    """Create an invoice and trigger webhook"""
    webhook_service = WebhookService(db)
    
    # Create invoice
    invoice = create_invoice_in_db(db, invoice_data, tenant_id)
    
    # Trigger webhook
    webhook_service.trigger_event(
        tenant_id=tenant_id,
        event="invoice.created",
        resource_type="invoice",
        resource_id=invoice.id,
        data={
            "invoice_number": invoice.number,
            "amount": str(invoice.total),
            "currency": invoice.currency,
            "customer": invoice.customer_name,
            "status": invoice.status,
        },
    )
    
    return invoice
```

---

## Webhook Events

### Eventos Soportados

#### Invoices

```python
# invoice.created
# Triggered: Cuando se crea una nueva factura
event = "invoice.created"
data = {
    "invoice_id": "inv-123",
    "invoice_number": "001-001-000000001",
    "amount": "1500.00",
    "currency": "USD",
    "customer": "Acme Corp",
    "status": "draft",
}

# invoice.sent
# Triggered: Cuando se envía la factura
event = "invoice.sent"
data = {
    "invoice_id": "inv-123",
    "invoice_number": "001-001-000000001",
    "sent_at": "2024-02-14T10:30:00",
}

# invoice.authorized
# Triggered: Cuando se autoriza en SRI
event = "invoice.authorized"
data = {
    "invoice_id": "inv-123",
    "authorization_number": "1234567890",
    "authorization_date": "2024-02-14T10:35:00",
}

# invoice.rejected
# Triggered: Cuando se rechaza en SRI
event = "invoice.rejected"
data = {
    "invoice_id": "inv-123",
    "rejection_reason": "Invalid RUC",
    "rejected_at": "2024-02-14T10:40:00",
}
```

#### Payments

```python
# payment.received
# Triggered: Cuando se recibe un pago
event = "payment.received"
data = {
    "payment_id": "pay-456",
    "invoice_id": "inv-123",
    "amount": "1500.00",
    "method": "bank_transfer",
    "reference": "TR-2024-001",
    "received_at": "2024-02-14T11:00:00",
}
```

#### Customers

```python
# customer.created
# Triggered: Cuando se crea un nuevo cliente
event = "customer.created"
data = {
    "customer_id": "cust-789",
    "business_name": "Acme Corp",
    "ruc": "1234567890001",
    "country": "Ecuador",
    "created_at": "2024-02-14T12:00:00",
}

# customer.updated
# Triggered: Cuando se actualiza un cliente
event = "customer.updated"
data = {
    "customer_id": "cust-789",
    "business_name": "Acme Corp Updated",
    "updated_at": "2024-02-14T12:05:00",
}
```

#### Sales Orders

```python
# sales_order.created
# Triggered: Cuando se crea una orden de venta
event = "sales_order.created"
data = {
    "order_id": "so-001",
    "customer_id": "cust-789",
    "amount": "2500.00",
    "items_count": 5,
    "created_at": "2024-02-14T13:00:00",
}

# sales_order.confirmed
# Triggered: Cuando se confirma la orden
event = "sales_order.confirmed"
data = {
    "order_id": "so-001",
    "confirmed_at": "2024-02-14T13:15:00",
}
```

---

## Integration Examples

### Ejemplo 1: Trigger en Invoice Creation (models/invoice.py)

```python
from sqlalchemy.orm import Session
from app.modules.webhooks.utils import WebhookFormatter
import json
from sqlalchemy import text

class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_invoice(self, data: dict, tenant_id: str):
        """Create invoice and trigger webhook"""
        
        # Create invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            number=data['number'],
            total=data['total'],
            currency=data['currency'],
            customer_name=data['customer_name'],
        )
        self.db.add(invoice)
        self.db.flush()  # Get the invoice ID before commit
        
        # Trigger webhook
        self._trigger_webhook(
            tenant_id=tenant_id,
            event="invoice.created",
            resource_id=str(invoice.id),
            data={
                "invoice_number": invoice.number,
                "amount": str(invoice.total),
                "currency": invoice.currency,
                "customer": invoice.customer_name,
            },
        )
        
        self.db.commit()
        return invoice
    
    def _trigger_webhook(self, tenant_id: str, event: str, resource_id: str, data: dict):
        """Internal webhook trigger"""
        # Find subscriptions
        subs = self.db.execute(
            text(
                """
                SELECT url, secret FROM webhook_subscriptions
                WHERE tenant_id = :tid AND event = :event AND active = true
                """
            ),
            {"tid": tenant_id, "event": event},
        ).fetchall()
        
        if not subs:
            return
        
        # Create delivery records
        payload = {
            "event": event,
            "resource_id": resource_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        
        for url, secret in subs:
            self.db.execute(
                text(
                    """
                    INSERT INTO webhook_deliveries(
                        tenant_id, event, payload, target_url, secret, status
                    )
                    VALUES (:tid, :event, :payload::jsonb, :url, :secret, 'PENDING')
                    """
                ),
                {
                    "tid": tenant_id,
                    "event": event,
                    "payload": json.dumps(payload),
                    "url": url,
                    "secret": secret,
                },
            )
```

### Ejemplo 2: Trigger desde API Endpoint

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import ensure_rls, tenant_id_from_request
from app.modules.invoices.service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.post("/", status_code=201)
def create_invoice(
    data: InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create invoice"""
    tenant_id = tenant_id_from_request(request)
    
    service = InvoiceService(db)
    invoice = service.create_invoice(data.dict(), tenant_id)
    
    return invoice
```

### Ejemplo 3: Verificar Webhooks en Cliente

```python
# Cliente que recibe webhooks
from fastapi import APIRouter, Request, HTTPException
from app.modules.webhooks.utils import WebhookSignature
import json

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = "your-webhook-secret-key"

@router.post("/gestiqcloud")
async def receive_webhook(request: Request):
    """Receive webhook from GestiqCloud"""
    
    # Get signature from header
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Signature header")
    
    # Get raw body
    body = await request.body()
    
    # Verify signature
    if not WebhookSignature.verify_raw(WEBHOOK_SECRET, body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    payload = json.loads(body)
    event = payload.get("event")
    
    # Handle event
    if event == "invoice.created":
        await handle_invoice_created(payload["data"])
    elif event == "payment.received":
        await handle_payment_received(payload["data"])
    
    return {"status": "ok"}

async def handle_invoice_created(data):
    """Handle invoice.created webhook"""
    print(f"Invoice created: {data['invoice_number']}")
    # Update your system...

async def handle_payment_received(data):
    """Handle payment.received webhook"""
    print(f"Payment received: {data['amount']}")
    # Update your system...
```

---

## Testing Webhooks

### Test 1: Crear Suscripción y Enviar Evento

```bash
#!/bin/bash

# 1. Create subscription
SUBSCRIPTION=$(curl -s -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "url": "https://webhook.site/12345-abcde",
    "secret": "my-webhook-secret"
  }' | jq '.id')

echo "Subscription created: $SUBSCRIPTION"

# 2. Trigger event
curl -s -X POST http://localhost:8000/api/v1/tenant/webhooks/deliveries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "payload": {
      "invoice_id": "inv-123",
      "amount": 1500.00,
      "customer": "Acme Corp"
    }
  }' | jq '.'

# 3. Check delivery status
sleep 2
curl -s -X GET "http://localhost:8000/api/v1/tenant/webhooks/deliveries?event=invoice.created" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.[] | {status, attempts, last_error}'
```

### Test 2: Test Signature Verification (Python)

```python
from app.modules.webhooks.utils import WebhookSignature
import json

# Payload
payload = {
    "invoice_id": "inv-123",
    "amount": 1500.00,
    "customer": "Acme Corp",
}

# Secret
secret = "my-webhook-secret"

# Sign
signature = WebhookSignature.sign(secret, payload)
print(f"Signature: {signature}")

# Verify
is_valid = WebhookSignature.verify(secret, payload, signature)
print(f"Valid: {is_valid}")

# Test tampered payload
tampered = {
    "invoice_id": "inv-123",
    "amount": 2000.00,  # Changed
    "customer": "Acme Corp",
}
is_valid = WebhookSignature.verify(secret, tampered, signature)
print(f"Valid (tampered): {is_valid}")  # Should be False
```

### Test 3: Webhook Testing Tool

Use [webhook.site](https://webhook.site/) para testing:

1. Ir a https://webhook.site/
2. Copiar la URL única
3. Crear suscripción con esa URL:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "event": "test.event",
       "url": "https://webhook.site/abc123xyz"
     }'
   ```
4. Enviar un evento:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tenant/webhooks/deliveries \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "event": "test.event",
       "payload": {"test": true}
     }'
   ```
5. Ver la solicitud recibida en webhook.site

---

## Checklist de Integración

- [ ] Importar `WebhookFormatter` y utilidades
- [ ] Añadir trigger en el punto donde se crea el recurso
- [ ] Definir payload con datos relevantes
- [ ] Testear con webhook.site
- [ ] Documentar el evento en este archivo
- [ ] Implementar validaciones de payload
- [ ] Añadir tests unitarios
- [ ] Testear en entorno de staging
- [ ] Actualizar documentación de API
