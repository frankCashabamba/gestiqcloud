# Webhooks Integration Plan - Step by Step

## Phase 1: Backend Integration (Invoicing Module)

### Step 1.1: Create Webhook Service Layer

Create file: `apps/backend/app/modules/invoicing/webhooks.py`

```python
"""
Webhook triggers for invoicing module
Handles sending webhook events when invoices are created, sent, authorized, etc.
"""

import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.webhooks.utils import WebhookFormatter

logger = logging.getLogger(__name__)


class InvoicingWebhookService:
    """Service for triggering webhooks from invoicing module"""

    def __init__(self, db: Session):
        self.db = db

    def trigger_invoice_created(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        amount: float,
        currency: str,
        customer_name: str,
        customer_id: Optional[str] = None,
    ) -> bool:
        """Trigger webhook when invoice is created"""
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.created",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "amount": str(amount),
                    "currency": currency,
                    "customer_name": customer_name,
                    "customer_id": customer_id,
                    "status": "draft",
                },
                tenant_id=str(tenant_id),
            )
            return self._enqueue_delivery(tenant_id, "invoice.created", payload)
        except Exception as e:
            logger.error(f"Error triggering invoice.created webhook: {e}")
            return False

    def trigger_invoice_sent(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
    ) -> bool:
        """Trigger webhook when invoice is sent"""
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.sent",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                },
                tenant_id=str(tenant_id),
            )
            return self._enqueue_delivery(tenant_id, "invoice.sent", payload)
        except Exception as e:
            logger.error(f"Error triggering invoice.sent webhook: {e}")
            return False

    def trigger_invoice_authorized(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        authorization_number: str,
    ) -> bool:
        """Trigger webhook when invoice is authorized in SRI"""
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.authorized",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "authorization_number": authorization_number,
                    "status": "authorized",
                },
                tenant_id=str(tenant_id),
            )
            return self._enqueue_delivery(tenant_id, "invoice.authorized", payload)
        except Exception as e:
            logger.error(f"Error triggering invoice.authorized webhook: {e}")
            return False

    def trigger_invoice_rejected(
        self,
        tenant_id: UUID,
        invoice_id: str,
        invoice_number: str,
        reason: str,
    ) -> bool:
        """Trigger webhook when invoice is rejected"""
        try:
            payload = WebhookFormatter.format_event_payload(
                event="invoice.rejected",
                resource_type="invoice",
                resource_id=invoice_id,
                data={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reason": reason,
                    "status": "rejected",
                },
                tenant_id=str(tenant_id),
            )
            return self._enqueue_delivery(tenant_id, "invoice.rejected", payload)
        except Exception as e:
            logger.error(f"Error triggering invoice.rejected webhook: {e}")
            return False

    def _enqueue_delivery(
        self, tenant_id: UUID, event: str, payload: Dict[str, Any]
    ) -> bool:
        """Internal method to enqueue webhook delivery"""
        try:
            # Check if there are active subscriptions for this event
            result = self.db.execute(
                text(
                    """
                    SELECT id FROM webhook_subscriptions
                    WHERE tenant_id = :tid AND event = :event AND active = true
                    LIMIT 1
                    """
                ),
                {"tid": str(tenant_id), "event": event},
            ).first()

            if not result:
                logger.debug(f"No active subscriptions for {event}")
                return False

            # Get all subscriptions for this event
            subs = self.db.execute(
                text(
                    """
                    SELECT url, secret FROM webhook_subscriptions
                    WHERE tenant_id = :tid AND event = :event AND active = true
                    """
                ),
                {"tid": str(tenant_id), "event": event},
            ).fetchall()

            # Create delivery records
            payload_json = json.dumps(payload)
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
                        "tid": str(tenant_id),
                        "event": event,
                        "payload": payload_json,
                        "url": url,
                        "secret": secret,
                    },
                )

            self.db.commit()
            logger.info(f"Enqueued {len(subs)} webhook deliveries for {event}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error enqueueing webhook delivery: {e}")
            return False
```

### Step 1.2: Integrate into Invoice Service

Edit: `apps/backend/app/modules/invoicing/services.py`

Add this at the top of the file:
```python
from app.modules.invoicing.webhooks import InvoicingWebhookService
```

Then, in your invoice creation method, add:
```python
def create_invoice(self, data: dict, tenant_id: UUID):
    """Create invoice"""
    # ... existing invoice creation code ...
    invoice = Invoice(...)
    self.db.add(invoice)
    self.db.flush()
    
    # Trigger webhook
    webhook_service = InvoicingWebhookService(self.db)
    webhook_service.trigger_invoice_created(
        tenant_id=tenant_id,
        invoice_id=str(invoice.id),
        invoice_number=invoice.number,
        amount=invoice.total,
        currency=invoice.currency or "USD",
        customer_name=invoice.customer_name,
        customer_id=invoice.customer_id,
    )
    
    self.db.commit()
    return invoice
```

Similar for other methods: `send_invoice`, `authorize_invoice`, `reject_invoice`

---

## Phase 2: Frontend UI Implementation

### Step 2.1: Complete Webhook Form Modal

Create: `apps/admin/src/features/webhooks/WebhookForm.tsx`

```typescript
import React, { useState } from 'react';
import { createWebhook, updateWebhook, Webhook } from '../../services/webhooks';
import './webhook-form.css';

interface WebhookFormProps {
  webhook?: Webhook;
  onClose: () => void;
  onSuccess?: () => void;
  eventOptions: string[];
}

const AVAILABLE_EVENTS = [
  'invoice.created',
  'invoice.sent',
  'invoice.authorized',
  'invoice.rejected',
  'invoice.cancelled',
  'payment.received',
  'payment.failed',
  'customer.created',
  'customer.updated',
  'sales_order.created',
  'sales_order.confirmed',
];

export const WebhookForm: React.FC<WebhookFormProps> = ({
  webhook,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    url: webhook?.url || '',
    events: webhook?.events || [],
    secret: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEventToggle = (event: string) => {
    setFormData((prev) => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.url) {
      setError('URL is required');
      return;
    }

    if (!formData.url.startsWith('https://')) {
      setError('URL must start with https://');
      return;
    }

    if (formData.events.length === 0) {
      setError('Select at least one event');
      return;
    }

    try {
      setLoading(true);
      if (webhook) {
        await updateWebhook(webhook.id, formData);
      } else {
        await createWebhook(formData);
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error saving webhook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="webhook-form-modal">
      <div className="webhook-form-modal__overlay" onClick={onClose} />
      <form className="webhook-form-modal__form" onSubmit={handleSubmit}>
        <div className="webhook-form-modal__header">
          <h2>{webhook ? 'Edit Webhook' : 'Create Webhook'}</h2>
          <button
            type="button"
            className="webhook-form-modal__close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {error && <div className="webhook-form-modal__error">{error}</div>}

        <div className="webhook-form-modal__body">
          <div className="webhook-form-modal__field">
            <label htmlFor="url">Webhook URL *</label>
            <input
              id="url"
              type="url"
              placeholder="https://your-app.com/webhook"
              value={formData.url}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, url: e.target.value }))
              }
              required
            />
          </div>

          <div className="webhook-form-modal__field">
            <label htmlFor="secret">Secret (Optional)</label>
            <input
              id="secret"
              type="password"
              placeholder="Enter webhook secret"
              value={formData.secret}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, secret: e.target.value }))
              }
            />
            <small>Minimum 8 characters</small>
          </div>

          <div className="webhook-form-modal__field">
            <label>Events *</label>
            <div className="webhook-form-modal__events">
              {AVAILABLE_EVENTS.map((event) => (
                <label key={event} className="webhook-form-modal__event-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.events.includes(event)}
                    onChange={() => handleEventToggle(event)}
                  />
                  {event}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="webhook-form-modal__footer">
          <button
            type="button"
            className="webhook-form-modal__cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="webhook-form-modal__submit"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
};
```

### Step 2.2: Update WebhooksPanel to use Form

Edit: `apps/admin/src/pages/WebhooksPanel.tsx`

```typescript
import React, { useState } from 'react';
import { WebhooksList } from '../features/webhooks/WebhooksList';
import { WebhookLogs } from '../features/webhooks/WebhookLogs';
import { WebhookForm } from '../features/webhooks/WebhookForm';
import { Webhook } from '../services/webhooks';

export const WebhooksPanel: React.FC = () => {
  const [selectedWebhook, setSelectedWebhook] = useState<Webhook | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);

  const handleEditWebhook = (webhook: Webhook) => {
    setEditingWebhook(webhook);
    setShowForm(true);
  };

  const handleCreateWebhook = () => {
    setEditingWebhook(null);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingWebhook(null);
  };

  const handleFormSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
    handleFormClose();
  };

  return (
    <div className="webhooks-panel">
      <div className="webhooks-panel__header">
        <h1 className="webhooks-panel__title">Webhooks</h1>
        <button
          className="webhooks-panel__create-btn"
          onClick={handleCreateWebhook}
        >
          + Nuevo Webhook
        </button>
      </div>

      <div className="webhooks-panel__content">
        <WebhooksList
          onEdit={handleEditWebhook}
          onRefresh={handleFormSuccess}
          key={refreshTrigger}
        />

        {selectedWebhook && (
          <div className="webhooks-panel__logs">
            <WebhookLogs webhookId={selectedWebhook.id} />
          </div>
        )}
      </div>

      {showForm && (
        <WebhookForm
          webhook={editingWebhook || undefined}
          onClose={handleFormClose}
          onSuccess={handleFormSuccess}
          eventOptions={[]}
        />
      )}
    </div>
  );
};
```

### Step 2.3: Add Webhook Form Styling

Create: `apps/admin/src/features/webhooks/webhook-form.css`

```css
.webhook-form-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.webhook-form-modal__overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  cursor: pointer;
}

.webhook-form-modal__form {
  position: relative;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.webhook-form-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.webhook-form-modal__header h2 {
  margin: 0;
  font-size: 18px;
}

.webhook-form-modal__close {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #666;
}

.webhook-form-modal__body {
  padding: 20px;
}

.webhook-form-modal__field {
  margin-bottom: 20px;
}

.webhook-form-modal__field label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.webhook-form-modal__field input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.webhook-form-modal__field small {
  display: block;
  margin-top: 4px;
  color: #999;
}

.webhook-form-modal__events {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.webhook-form-modal__event-checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.webhook-form-modal__event-checkbox input {
  margin-right: 8px;
  width: auto;
}

.webhook-form-modal__error {
  padding: 12px;
  background: #fee;
  color: #c33;
  border-radius: 4px;
  margin-bottom: 16px;
}

.webhook-form-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.webhook-form-modal__cancel,
.webhook-form-modal__submit {
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.webhook-form-modal__cancel {
  background: #f0f0f0;
  color: #333;
}

.webhook-form-modal__cancel:hover {
  background: #e0e0e0;
}

.webhook-form-modal__submit {
  background: #0066cc;
  color: white;
}

.webhook-form-modal__submit:hover:not(:disabled) {
  background: #0052a3;
}

.webhook-form-modal__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

---

## Phase 3: Integration Implementation

### Step 3.1: Add to Invoicing Service

In `services.py`, integrate the webhook calls:

```python
# At invoice creation
webhook_service = InvoicingWebhookService(db)
webhook_service.trigger_invoice_created(...)

# At invoice send
webhook_service.trigger_invoice_sent(...)

# At SRI authorization
webhook_service.trigger_invoice_authorized(...)

# At rejection
webhook_service.trigger_invoice_rejected(...)
```

### Step 3.2: Celery Configuration

Ensure Celery is running:
```bash
celery -A apps.backend.celery_app worker -l info
```

---

## Phase 4: Testing

### Test via curl

```bash
# 1. Create subscription
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "url": "https://webhook.site/unique-id",
    "secret": "test-secret-key"
  }'

# 2. Create invoice (triggers webhook)
# Use your invoice creation endpoint

# 3. Check delivery status
curl http://localhost:8000/api/v1/tenant/webhooks/deliveries \
  -H "Authorization: Bearer TOKEN"
```

### Test via webhook.site
1. Go to https://webhook.site/
2. Copy URL
3. Create subscription with that URL
4. Create invoice
5. See request in webhook.site

---

## Phase 5: Monitoring

### Check webhook logs
```sql
SELECT 
  id, 
  event, 
  status, 
  attempts, 
  last_error, 
  created_at 
FROM webhook_deliveries
WHERE event = 'invoice.created'
ORDER BY created_at DESC
LIMIT 20;
```

### Monitor failed deliveries
```sql
SELECT 
  target_url, 
  last_error, 
  COUNT(*) as count
FROM webhook_deliveries
WHERE status = 'FAILED'
GROUP BY target_url, last_error;
```

---

## Checklist

- [ ] Create `webhooks.py` in invoicing module
- [ ] Add InvoicingWebhookService class
- [ ] Integrate webhook calls in invoice service
- [ ] Create WebhookForm.tsx component
- [ ] Update WebhooksPanel.tsx
- [ ] Add webhook-form.css styling
- [ ] Test with curl/webhook.site
- [ ] Monitor deliveries
- [ ] Document in module README
- [ ] Add similar integration for:
  - [ ] Payment module
  - [ ] Customer module
  - [ ] Sales Order module

---

## Expected Outcome

✅ Webhooks triggered automatically on invoice events
✅ Complete UI for managing webhooks
✅ Real-time testing capability
✅ Full audit trail of deliveries
✅ Production-ready integration

---

**Status:** Ready to implement
**Estimated Time:** 2-3 hours for invoicing, 1 hour each for other modules
