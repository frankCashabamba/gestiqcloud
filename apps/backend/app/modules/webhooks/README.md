# Webhooks Module

Módulo completo de gestión de webhooks para GestiqCloud. Permite que los tenants se suscriban a eventos de la plataforma y reciban notificaciones en sus endpoints mediante entregas con firma HMAC-SHA256.

## Características

- ✅ Gestión de suscripciones por tenant con RLS
- ✅ Validación de URLs HTTPS
- ✅ Firma HMAC-SHA256 con SHA256 hash
- ✅ Detección de suscripciones duplicadas
- ✅ Entregas asincrónicas con Celery
- ✅ Reintentos con backoff exponencial
- ✅ Manejo robusto de errores
- ✅ Logging estructurado
- ✅ Tests unitarios completos

## Autenticación y Tenancy

- Todas las rutas requieren autenticación Bearer token
- Endpoints bajo `/api/v1/tenant/webhooks` con prefix `/tenant`
- Header `X-Tenant-Id` puede ser requerido según middleware
- RLS (Row Level Security) aplicado automáticamente

## Endpoints

### Subscriptions (Suscripciones)

#### POST `/api/v1/tenant/webhooks/subscriptions`

Crear una nueva suscripción a un evento.

**Request:**
```json
{
  "event": "invoice.created",
  "url": "https://yourapp.com/webhook",
  "secret": "your-webhook-secret-key"  // Opcional, mínimo 8 caracteres
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "invoice.created",
  "url": "https://yourapp.com/webhook",
  "secret": "***",  // Masked en respuesta
  "active": true,
  "created_at": "2024-02-14T10:30:00"
}
```

**Errores:**
- `400`: Validación fallida (URL no HTTPS, evento vacío, secret muy corto)
- `409`: Suscripción duplicada (mismo event+url ya activo)
- `403`: Contexto de tenant faltante

---

#### GET `/api/v1/tenant/webhooks/subscriptions`

Listar suscripciones activas del tenant.

**Query Parameters:**
- `event` (opcional): Filtrar por nombre de evento

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "event": "invoice.created",
    "url": "https://yourapp.com/webhook",
    "secret": "***",
    "active": true,
    "created_at": "2024-02-14T10:30:00"
  }
]
```

---

#### DELETE `/api/v1/tenant/webhooks/subscriptions/{subscription_id}`

Desactivar (soft delete) una suscripción.

**Response (204):** No content

**Errores:**
- `404`: Suscripción no encontrada
- `403`: No autorizado

---

### Deliveries (Entregas)

#### POST `/api/v1/tenant/webhooks/deliveries`

Encolar entregas de webhook para un evento específico.

**Request:**
```json
{
  "event": "invoice.created",
  "payload": {
    "invoice_id": "inv-123",
    "amount": 1500.00,
    "currency": "USD",
    "customer": "Acme Corp"
  }
}
```

**Response (202):**
```json
{
  "queued": true,
  "count": 2,
  "message": "Enqueued 2 deliveries"
}
```

**Errores:**
- `400`: Validación fallida (event/payload inválido)
- `404`: No hay suscripciones activas para ese evento
- `403`: Contexto de tenant faltante

---

#### GET `/api/v1/tenant/webhooks/deliveries`

Listar entregas de webhook del tenant (últimas 100).

**Query Parameters:**
- `event` (opcional): Filtrar por evento
- `status` (opcional): Filtrar por estado (PENDING, SENDING, SENT, DELIVERED, FAILED)

**Response (200):**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "event": "invoice.created",
    "status": "DELIVERED",
    "attempts": 1,
    "target_url": "https://yourapp.com/webhook",
    "last_error": null,
    "created_at": "2024-02-14T10:35:00",
    "updated_at": "2024-02-14T10:35:15"
  }
]
```

---

#### GET `/api/v1/tenant/webhooks/deliveries/{delivery_id}`

Obtener detalles de una entrega específica.

**Response (200):** Objeto de entrega detallado

**Errores:**
- `404`: Entrega no encontrada

---

#### POST `/api/v1/tenant/webhooks/deliveries/{delivery_id}/retry`

Reintentar una entrega fallida.

**Response (202):**
```json
{
  "queued": true,
  "message": "Retry queued"
}
```

**Errores:**
- `404`: Entrega no encontrada
- `400`: Entrega no está en estado fallido

---

## Modelos de Base de Datos

### `webhook_subscriptions`

```sql
CREATE TABLE webhook_subscriptions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    secret VARCHAR(500),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indices recomendados
CREATE INDEX idx_webhook_subscriptions_tenant_event ON webhook_subscriptions(tenant_id, event);
CREATE INDEX idx_webhook_subscriptions_active ON webhook_subscriptions(active);
```

### `webhook_deliveries`

```sql
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    secret VARCHAR(500),
    status VARCHAR(20) DEFAULT 'PENDING',
    attempts INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indices recomendados
CREATE INDEX idx_webhook_deliveries_tenant_status ON webhook_deliveries(tenant_id, status);
CREATE INDEX idx_webhook_deliveries_tenant_event ON webhook_deliveries(tenant_id, event);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
```

---

## Flujo de Entrega

```
POST /deliveries
    ↓
Find active subscriptions for event
    ↓
Insert webhook_deliveries records (status=PENDING)
    ↓
Send Celery task: apps.backend.app.modules.webhooks.tasks.deliver
    ↓
[Async Task]
    ├─ Fetch delivery record
    ├─ Calculate HMAC-SHA256 signature
    ├─ POST to target_url with headers:
    │   ├─ Content-Type: application/json
    │   ├─ X-Event: <event_name>
    │   ├─ X-Signature: sha256=<hex_digest>
    │   └─ User-Agent: GestiqCloud-Webhooks/1.0
    ├─ Check response
    │   ├─ 2xx/3xx → status=DELIVERED ✓
    │   ├─ 4xx → status=FAILED (no retry)
    │   └─ 5xx/timeout/error → Retry with backoff
    └─ Update status in webhook_deliveries
```

---

## Firma HMAC

### Generación (lado servidor)

La firma se calcula sobre el JSON raw del payload:

```python
import hmac
import hashlib
import json

payload = {"invoice_id": "inv-123", "amount": 1500.00}
secret = "your-webhook-secret-key"

# Serializar JSON de forma determinista
body_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

# Generar HMAC-SHA256
signature = hmac.new(
    secret.encode("utf-8"),
    body_bytes,
    hashlib.sha256
).hexdigest()

# Header X-Signature
header = f"sha256={signature}"
```

### Verificación (lado cliente)

```python
import hmac
import hashlib
import json

# Recibir header
x_signature = "sha256=abcd1234..."  # Del header X-Signature

# Recibir body como string JSON raw
body_raw = request.body  # Raw request body

# Recalcular firma
secret = "your-webhook-secret-key"
expected_sig = hmac.new(
    secret.encode("utf-8"),
    body_raw,
    hashlib.sha256
).hexdigest()

# Comparar
import hmac
if hmac.compare_digest(expected_sig, x_signature.replace("sha256=", "")):
    print("Firma válida ✓")
else:
    print("Firma inválida ✗")
```

---

## Configuración

### Variables de Entorno

```env
# Celery (si se usa cola de tareas)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Webhooks
WEBHOOK_TIMEOUT_SECONDS=10              # Timeout por request (default: 10s)
WEBHOOK_MAX_RETRIES=3                   # Máximo reintentos (default: 3)
WEBHOOK_USER_AGENT=GestiqCloud-Webhooks/1.0
```

### Reintentos

- **Intento 1:** Inmediato
- **Intento 2:** 2^1 = 2 segundos
- **Intento 3:** 2^2 = 4 segundos
- **Intento 4:** 2^3 = 8 segundos

Total: ~14 segundos de reintentos

---

## Seguridad

### Validaciones

✅ **URL:**
- Obligatoriamente HTTPS
- Máximo 2048 caracteres
- Válida según RFC 3986

✅ **Secret:**
- Mínimo 8 caracteres
- Máximo 500 caracteres
- Nunca se retorna en la API (solo "***")

✅ **Event:**
- Minúscula/normalizada
- Sin espacios
- Máximo 100 caracteres

✅ **Payload:**
- JSON serializable
- Sin límite de tamaño (considerar validación custom)

### RLS (Row Level Security)

```sql
-- Solo se accede a datos del tenant actual
ALTER TABLE webhook_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY webhook_subscriptions_tenant_policy
ON webhook_subscriptions
USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Logging

```python
import logging

logger = logging.getLogger("app.modules.webhooks")

# Nivel INFO
logger.info(f"Webhook delivered successfully: {delivery_id} (HTTP 200)")
logger.info("Queued delivery task: 660e8400-...")

# Nivel WARNING
logger.warning(f"Webhook delivery timeout: {delivery_id}")
logger.warning(f"Webhook delivery connection error: {delivery_id}")

# Nivel ERROR
logger.error(f"Failed to queue Celery task: {error}")
logger.error(f"Webhook delivery failed after 3 attempts: {delivery_id}")
```

**No se loggean:**
- Secrets ni claves API
- Payloads completos (pueden contener datos sensibles)
- Request/response bodies completos

---

## Ejemplos de Uso

### Crear Suscripción

```bash
curl -X POST https://localhost/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "url": "https://webhook.site/unique-id",
    "secret": "my-webhook-secret-key"
  }'
```

### Listar Suscripciones

```bash
curl -X GET "https://localhost/api/v1/tenant/webhooks/subscriptions?event=invoice.created" \
  -H "Authorization: Bearer eyJhbGc..."
```

### Encolar Entrega

```bash
curl -X POST https://localhost/api/v1/tenant/webhooks/deliveries \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "payload": {
      "invoice_id": "inv-001",
      "amount": 1500.00,
      "status": "sent"
    }
  }'
```

### Verificar Entrega

```bash
curl -X GET https://localhost/api/v1/tenant/webhooks/deliveries/660e8400-... \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## Estructura del Módulo

```
webhooks/
├── README.md                              # This file
├── tasks.py                               # Celery tasks
├── domain/
│   └── entities.py                        # Domain models
├── infrastructure/
│   └── webhook_dispatcher.py              # Dispatcher (legacy)
└── interface/
    └── http/
        └── tenant.py                      # API endpoints
```

---

## Testing

Ejecutar tests:

```bash
pytest apps/backend/tests/test_webhooks.py -v
```

Tests incluyen:
- ✅ Validación de entrada
- ✅ Generación y verificación de firmas
- ✅ Manejo de errores
- ✅ Serialización de payloads

---

## Migration

Ejecutar migración:

```bash
cd apps/backend
alembic upgrade head
```

---

## Troubleshooting

### 404: No active subscriptions for event
- Verificar que haya suscripciones activas: `GET /subscriptions?event=...`
- Verificar que `active=true` en la BD
- Verificar que el tenant_id sea correcto

### 409: Duplicate subscription
- Ya existe una suscripción activa con el mismo event+url
- Desactivar con DELETE si es necesario

### Webhook no se recibe
1. Verificar en `webhook_deliveries` el estado y `last_error`
2. Verificar logs del servidor: `grep "Webhook delivery" backend.log`
3. Verificar que la URL sea alcanzable: `curl -X POST https://...`
4. Verificar que se calcula bien la firma HMAC

### Celery no envía tareas
- Verificar `CELERY_BROKER_URL` configurado
- Verificar Redis/RabbitMQ está ejecutándose
- Ver logs de Celery worker

---

## Roadmap Futuro

- [ ] Webhooks entrantes (receiving webhooks de terceros)
- [ ] Webhooks por resource (no solo por event)
- [ ] Filtros avanzados en suscripciones
- [ ] Webhook replay desde UI
- [ ] Rate limiting por endpoint
- [ ] Circuit breaker pattern
- [ ] Batching de eventos
- [ ] Webhook templates

---

## Referencias

- [HMAC RFC 2104](https://tools.ietf.org/html/rfc2104)
- [JSON Web Signature (JWS) RFC 7515](https://tools.ietf.org/html/rfc7515)
- [Stripe Webhooks Documentation](https://stripe.com/docs/webhooks)
- [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
