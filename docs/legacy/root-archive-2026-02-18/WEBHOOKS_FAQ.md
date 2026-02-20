# Webhooks Module - FAQ & Troubleshooting

## Preguntas Frecuentes

### General

#### P: ¿Qué es el módulo de webhooks?
**R:** Sistema para que los tenants se suscriban a eventos de GestiqCloud y reciban notificaciones en tiempo real a través de HTTP POST a sus endpoints.

#### P: ¿Es obligatorio usar Celery?
**R:** No. Los webhooks funcionan sin Celery, pero la entrega será sincrónica y bloqueante. Con Celery es asincrónica y más escalable. Recomendado: usar Celery en producción.

#### P: ¿Qué eventos están soportados?
**R:** 14+ eventos predefinidos (invoice, payment, customer, sales_order, etc.). Puedes agregar más editando `domain/entities.py` → `WebhookEventType` enum.

#### P: ¿Es seguro?
**R:** Sí, es muy seguro:
- URLs HTTPS obligatorias
- HMAC-SHA256 con timing attack protection
- RLS (tenant isolation)
- Secrets mascarados en logs
- Input validation con Pydantic

---

## Problemas Comunes

### 1. 404 Not Found en GET /webhooks/subscriptions

**Problema:**
```
GET /webhooks/subscriptions HTTP/1.1" 404 Not Found
```

**Causa:** Ruta incorrecta. Los webhooks están bajo `/api/v1/tenant/webhooks`, no `/webhooks`.

**Solución:**
```bash
# ❌ Incorrecto
curl http://localhost:8000/webhooks/subscriptions

# ✅ Correcto
curl http://localhost:8000/api/v1/tenant/webhooks/subscriptions
```

---

### 2. 409 Conflict: Duplicate Subscription

**Problema:**
```json
{
  "detail": "duplicate_subscription"
}
```

**Causa:** Ya existe una suscripción activa con el mismo event+url.

**Solución:**
```bash
# 1. Listar suscripciones existentes
curl http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer TOKEN" | jq '.'

# 2. Desactivar la suscripción duplicada
curl -X DELETE http://localhost:8000/api/v1/tenant/webhooks/subscriptions/{id} \
  -H "Authorization: Bearer TOKEN"

# 3. Crear nueva suscripción
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

### 3. 400 Bad Request: URL must use HTTPS

**Problema:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "url"],
      "msg": "URL must use HTTPS protocol"
    }
  ]
}
```

**Causa:** URL comienza con `http://` en lugar de `https://`.

**Solución:**
```bash
# ❌ Incorrecto
"url": "http://webhook.example.com/hook"

# ✅ Correcto
"url": "https://webhook.example.com/hook"
```

---

### 4. 400 Bad Request: secret must be at least 8 characters

**Problema:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "secret"],
      "msg": "Secret must be at least 8 characters"
    }
  ]
}
```

**Causa:** Secret muy corto.

**Solución:**
```bash
# ❌ Incorrecto (7 caracteres)
"secret": "mysecr"

# ✅ Correcto (mínimo 8)
"secret": "my-secret-key-12345"
```

---

### 5. 404 Not Found: no_active_subscriptions_for_event

**Problema:**
```json
{
  "detail": "no_active_subscriptions_for_event"
}
```

**Causa:** Intentas encolar una entrega pero no hay suscripciones activas para ese evento.

**Solución:**
```bash
# 1. Verificar si hay suscripciones
curl "http://localhost:8000/api/v1/tenant/webhooks/subscriptions?event=invoice.created" \
  -H "Authorization: Bearer TOKEN" | jq '.'

# 2. Crear una suscripción si no existe
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "url": "https://webhook.example.com/invoices",
    "secret": "my-secret-key"
  }'

# 3. Intentar encolar de nuevo
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/deliveries \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invoice.created",
    "payload": {"invoice_id": "inv-123"}
  }'
```

---

### 6. Webhook no se recibe en el servidor

**Problema:** Ejecutas POST /deliveries pero no recibes nada en tu endpoint.

**Paso a paso para diagnosticar:**

#### 1. Verificar que existe la entrega
```bash
curl "http://localhost:8000/api/v1/tenant/webhooks/deliveries?event=invoice.created" \
  -H "Authorization: Bearer TOKEN" | jq '.[0]'
```

Deberías ver:
```json
{
  "id": "660e8400-...",
  "event": "invoice.created",
  "status": "DELIVERED",  // or "FAILED", "PENDING"
  "attempts": 1,
  "target_url": "https://your-endpoint.com/webhook",
  "last_error": null,
  "created_at": "2024-02-14T10:35:00"
}
```

#### 2. Si status es "FAILED", revisar error
```bash
curl "http://localhost:8000/api/v1/tenant/webhooks/deliveries/660e8400-..." \
  -H "Authorization: Bearer TOKEN" | jq '.last_error'
```

Errores comunes:
- `Connection error: [Errno 111] Connection refused` → Tu servidor no está escuchando
- `HTTP 404` → Tu endpoint no existe
- `Request timeout (10s)` → Tu servidor tarda >10s en responder
- `Connection error: nodename nor servname provided` → Domain no resuelve

#### 3. Si status es "PENDING", aguarda
Celery está intentando entregarla. Espera unos segundos y vuelve a verificar.

#### 4. Verificar logs del backend
```bash
tail -f backend.log | grep -i webhook
```

Deberías ver:
```
INFO:     Attempting webhook delivery 1/3: invoice.created to https://...
INFO:     Webhook delivered successfully: 660e8400-... (HTTP 200)
```

#### 5. Probar conexión manual
```bash
curl -X POST https://your-endpoint.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": true}' -v
```

---

### 7. Error de firma HMAC inválida

**Problema:** Tu servidor rechaza los webhooks por firma inválida.

**Causa:** Cálculo incorrecto de la firma o secret incorrecto.

**Solución:**

##### En el servidor (verifica así):
```python
import hmac
import hashlib
import json

def verify_signature(request_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify webhook signature"""
    # El signature_header viene como: "sha256=abc123..."

    # Recalcular firma del body raw
    calculated_sig = hmac.new(
        secret.encode('utf-8'),
        request_body,  # IMPORTANTE: usar el body raw, no parseado
        hashlib.sha256
    ).hexdigest()

    # Extraer hex del header
    _, header_hex = signature_header.split('=')

    # Comparar con constant-time comparison
    return hmac.compare_digest(calculated_sig, header_hex)

# Uso en FastAPI
from fastapi import Request, HTTPException

@app.post("/webhook")
async def receive_webhook(request: Request):
    # Obtener headers
    signature = request.headers.get("X-Signature")
    secret = "my-secret-key"

    # Obtener body raw
    body = await request.body()

    # Verificar
    if not verify_signature(body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Procesar webhook
    payload = json.loads(body)
    return {"status": "ok"}
```

##### O usar la utilidad de GestiqCloud:
```python
from app.modules.webhooks.utils import WebhookSignature
from fastapi import Request, HTTPException

@app.post("/webhook")
async def receive_webhook(request: Request):
    signature = request.headers.get("X-Signature")
    body = await request.body()
    secret = "my-secret-key"

    if not WebhookSignature.verify_raw(secret, body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    return {"status": "ok"}
```

---

### 8. Secret no aparece en respuesta (aparece "***")

**Comportamiento esperado.** El secret nunca se retorna en las respuestas API. Esto es por seguridad. Si necesitas ver el secret, debes guardarlo en tu cliente cuando lo creas.

---

### 9. Celery no envía tareas

**Problema:** Los webhooks no se envían, status permanece en PENDING.

**Causa:** Celery no está configurado o el broker no está disponible.

**Verificar:**

1. **¿Está configurado CELERY_BROKER_URL?**
```bash
echo $CELERY_BROKER_URL
# Debería mostrar: redis://localhost:6379/0 o similar
```

2. **¿Está corriendo Redis/RabbitMQ?**
```bash
# Si usas Redis
redis-cli ping
# Debería retornar: PONG

# Si usas RabbitMQ
sudo systemctl status rabbitmq-server
```

3. **¿Está corriendo el Celery worker?**
```bash
celery -A apps.backend.celery_app worker -l info
```

4. **Solución:** Si Celery no está disponible, los webhooks se enviarán sincronicamente (pero bloqueante):
   - Sin Celery: requests.post() sucede en el request actual
   - Con Celery: send_task() solo la encola (no bloquea)

---

### 10. Demasiados reintentos

**Problema:** Un webhook falla y reintenta muchas veces, saturando el endpoint.

**Comportamiento normal:**
- Máximo 3 reintentos por defecto
- Backoff exponencial: 1s, 2s, 4s entre reintentos
- Total: ~7 segundos hasta marcar como fallido

**Si quieres menos reintentos:**
Editar `apps/backend/app/modules/webhooks/tasks.py`:
```python
@shared_task(
    name="...",
    bind=True,
    max_retries=1,  # Cambiar de 3 a 1
    default_retry_delay=30,  # Cambiar delay
)
```

**Si quieres deshabilitar reintentos:**
```python
@shared_task(
    name="...",
    bind=True,
    max_retries=0,  # Sin reintentos
)
```

---

### 11. Webhook malformado (error JSON)

**Problema:** Recibes un error JSON en el cliente.

**Causa:** El payload no es JSON válido.

**Solución:** El módulo valida que sea JSON serializable antes de enviar. Si llega aquí es un bug. Reportar en logs:

```bash
grep "Failed to parse payload JSON" backend.log
```

---

## Configuración Avanzada

### Cambiar timeout de webhook

```bash
# .env
WEBHOOK_TIMEOUT_SECONDS=30  # default: 10
```

### Cambiar máximo de reintentos

```bash
# .env (requiere cambio en tasks.py)
WEBHOOK_MAX_RETRIES=5  # default: 3
```

### Cambiar User-Agent

```bash
# .env
WEBHOOK_USER_AGENT=MyApp-Webhooks/2.0
```

---

## Monitoreo

### Ver webhooks pendientes
```sql
SELECT COUNT(*) FROM webhook_deliveries
WHERE tenant_id = 'abc123' AND status = 'PENDING';
```

### Ver webhooks fallidos
```sql
SELECT id, target_url, last_error, attempts FROM webhook_deliveries
WHERE tenant_id = 'abc123' AND status = 'FAILED'
ORDER BY created_at DESC LIMIT 10;
```

### Ver estadísticas
```sql
SELECT
  status,
  COUNT(*) as count,
  AVG(attempts) as avg_attempts
FROM webhook_deliveries
WHERE tenant_id = 'abc123'
GROUP BY status;
```

### Ver webhook más lento
```sql
SELECT
  id,
  target_url,
  EXTRACT(EPOCH FROM (updated_at - created_at)) as duration_seconds,
  attempts
FROM webhook_deliveries
WHERE tenant_id = 'abc123' AND status = 'DELIVERED'
ORDER BY (updated_at - created_at) DESC LIMIT 1;
```

---

## Testing

### Usar webhook.site para testing
1. Ir a https://webhook.site/
2. Copiar URL
3. Crear suscripción con esa URL
4. Encolar delivery
5. Ver solicitud en webhook.site

### Test local con netcat
```bash
# Terminal 1: Escuchar en puerto 8888
nc -l -p 8888

# Terminal 2: Encolar delivery a localhost:8888
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/deliveries \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "test",
    "payload": {"test": true}
  }'

# Terminal 3 (opcional): Cambiar URL de suscripción
curl -X DELETE http://localhost:8000/api/v1/tenant/webhooks/subscriptions/{id} \
  -H "Authorization: Bearer TOKEN"
curl -X POST http://localhost:8000/api/v1/tenant/webhooks/subscriptions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "test",
    "url": "http://localhost:8888",
    "secret": "test-secret"
  }'
```

---

## Migración

### ¿Necesito crear las tablas manualmente?

No, la migración lo hace automáticamente:

```bash
cd apps/backend
alembic upgrade head
```

### ¿Cómo deshacer si cometo un error?

```bash
# Ver migraciones
alembic current
alembic history

# Retroceder a versión anterior
alembic downgrade 011_accounting_settings_ap_expense
```

---

## Contratación de Personal (Personas)

Si necesitas:
- **Implementar triggers** en otros módulos → Software Engineer (Python/FastAPI)
- **UI para webhooks** en admin → Frontend Engineer (React/TypeScript)
- **Monitoreo** → DevOps Engineer
- **Testing** → QA Engineer

---

## Roadmap Futuro

- [ ] Webhook retry UI en admin panel
- [ ] Circuit breaker pattern (no enviar si endpoint falla 10 veces)
- [ ] Rate limiting (máx X webhooks/minuto por endpoint)
- [ ] Webhook templates (transformaciones de payload)
- [ ] Signature con JWT en lugar de HMAC (opcional)
- [ ] Webhook batching (agrupar eventos)
- [ ] Webhook replay desde UI
- [ ] Webhook analytics (gráficos de delivery)

---

## Referencias

- [RFC 2104 - HMAC](https://tools.ietf.org/html/rfc2104)
- [OWASP - Timing Attacks](https://owasp.org/www-community/attacks/Timing_attack)
- [Stripe Webhooks Best Practices](https://stripe.com/docs/webhooks/best-practices)
- [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks)

---

**Última actualización:** 2024-02-14
**Versión:** 1.0.0
