# Migration 140: Sistema de Notificaciones Multi-Canal

**Fecha**: 2025-01-28  
**Autor**: Sistema  
**Tipo**: Feature

## Descripción

Implementa sistema completo de notificaciones multi-canal con soporte para:
- **Email** vía SMTP (Gmail, SendGrid, etc)
- **WhatsApp** vía Twilio o API genérica
- **Telegram** vía Bot API

Incluye:
- Configuración de canales por tenant
- Log completo de notificaciones enviadas
- Alertas automáticas de stock bajo
- Plantillas reutilizables (Jinja2)

## Tablas Creadas

### notification_channels
Canales de notificación configurados por tenant.

**Campos clave**:
- `tipo`: 'email', 'whatsapp', 'telegram'
- `config`: Configuración específica (JSONB)
- `use_for_alerts`: Usar para alertas de stock
- `use_for_invoices`: Usar para facturas
- `use_for_marketing`: Usar para campañas

### notification_logs
Auditoría completa de todas las notificaciones enviadas.

**Campos clave**:
- `estado`: 'pending', 'sent', 'failed', 'bounced'
- `ref_type` + `ref_id`: Referencia al documento (invoice, order, etc)
- `metadata`: Datos adicionales (message_id, tracking_id)

### stock_alerts
Alertas de stock bajo generadas automáticamente.

**Campos clave**:
- `nivel_actual` vs `nivel_minimo`
- `diferencia`: Calculado automáticamente
- `notified_at` + `notified_via`: Tracking de notificación

### notification_templates
Plantillas reutilizables con variables Jinja2.

**Campos clave**:
- `codigo`: Identificador único ('invoice_sent', 'stock_low')
- `mensaje_template`: Plantilla Jinja2
- `variables`: Mapa de variables disponibles

## Funciones SQL

### check_low_stock()
```sql
SELECT check_low_stock();
```

Genera alertas para productos con stock por debajo del mínimo:
1. Compara `stock_items.qty_on_hand` vs `products.stock_min`
2. Crea alerta si stock < mínimo
3. Resuelve alertas donde stock se recuperó
4. Evita duplicados (últimas 24h)

**Uso**: Ejecutar cada hora vía Celery Beat

## Workers Celery

### send_notification_task(tenant_id, tipo, destinatario, asunto, mensaje)
Envía notificación async por el canal configurado.

### check_and_notify_low_stock()
Tarea programada (cada hora):
1. Ejecuta `check_low_stock()`
2. Agrupa alertas por tenant
3. Envía notificación por cada canal activo
4. Marca alertas como notificadas

### send_invoice_notification(invoice_id, tipo)
Notifica al cliente sobre una factura.

### cleanup_old_logs(days=90)
Limpia logs antiguos (mensual).

## Endpoints API

```
# Canales
GET    /api/v1/notifications/channels
POST   /api/v1/notifications/channels
GET    /api/v1/notifications/channels/{id}
PUT    /api/v1/notifications/channels/{id}
DELETE /api/v1/notifications/channels/{id}

# Envío
POST   /api/v1/notifications/test      # Enviar prueba
POST   /api/v1/notifications/send      # Envío manual

# Log
GET    /api/v1/notifications/log
GET    /api/v1/notifications/log/stats

# Alertas
GET    /api/v1/notifications/alerts
POST   /api/v1/notifications/alerts/{id}/resolve
```

## Configuración Canales

### Email (SMTP)
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "noreply@gestiqcloud.com",
  "smtp_password": "***",
  "from_email": "GestiQCloud <noreply@gestiqcloud.com>",
  "use_tls": true,
  "default_recipient": "admin@empresa.com"
}
```

### WhatsApp (Twilio)
```json
{
  "provider": "twilio",
  "account_sid": "ACxxxx",
  "auth_token": "***",
  "from_number": "+14155238886",
  "default_recipient": "+593987654321"
}
```

### WhatsApp (API Genérica)
```json
{
  "provider": "generic",
  "api_url": "https://api.whatsapp.example.com/send",
  "api_key": "***",
  "default_recipient": "+593987654321"
}
```

### Telegram
```json
{
  "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "parse_mode": "HTML",
  "default_recipient": "123456789"
}
```

## Dependencias Python

```bash
# Email
# (stdlib, incluido en Python)

# WhatsApp (Twilio)
pip install twilio

# Telegram
# (requests, ya incluido)

# Celery
pip install celery redis
```

## Variables de Entorno

```bash
# Email (default para todos los tenants)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@gestiqcloud.com
SMTP_PASSWORD=***

# Celery Beat
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Configurar Celery Beat

En `apps/backend/app/config/celery_config.py`:

```python
from celery.schedules import crontab

beat_schedule = {
    'check-low-stock-every-hour': {
        'task': 'app.workers.notifications.check_and_notify_low_stock',
        'schedule': crontab(minute=0),  # Cada hora en punto
    },
    'cleanup-old-logs-monthly': {
        'task': 'app.workers.notifications.cleanup_old_logs',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # Día 1 a las 2 AM
        'kwargs': {'days': 90}
    }
}
```

## Testing

### 1. Configurar Canal Email
```bash
curl -X POST http://localhost:8000/api/v1/notifications/channels \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "email",
    "nombre": "SMTP Gmail",
    "config": {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "test@gmail.com",
      "smtp_password": "***",
      "from_email": "test@gmail.com",
      "use_tls": true,
      "default_recipient": "admin@empresa.com"
    },
    "use_for_alerts": true
  }'
```

### 2. Enviar Prueba
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "uuid-del-canal",
    "destinatario": "test@example.com"
  }'
```

### 3. Ver Log
```bash
curl http://localhost:8000/api/v1/notifications/log?days=7
```

### 4. Generar Alertas Stock
```sql
-- En psql
SELECT check_low_stock();

-- Ver alertas generadas
SELECT * FROM stock_alerts WHERE estado = 'active';
```

### 5. Ejecutar Worker Manualmente
```python
from app.workers.notifications import check_and_notify_low_stock
check_and_notify_low_stock.delay()
```

## Seguridad

- ✅ **RLS**: Políticas aplicadas a todas las tablas
- ✅ **Secrets**: Configuración en JSONB cifrado
- ✅ **Validación**: Input validation en schemas
- ✅ **Rate Limiting**: Implementar en producción (Redis)
- ⚠️ **Recomendación**: Usar secrets manager (AWS Secrets, Vault) para passwords

## Rollback

```bash
psql -U postgres -d gestiqclouddb_dev -f down.sql
```

## Notas

- Celery Beat debe estar corriendo para tareas programadas
- Configurar límites de envío por hora/día según proveedor
- WhatsApp Twilio requiere número verificado
- Telegram bot: crear con @BotFather
- Gmail App Passwords: https://support.google.com/accounts/answer/185833

## Estado

- ✅ Tablas creadas
- ✅ RLS aplicado
- ✅ Función check_low_stock()
- ✅ Workers Celery
- ✅ Endpoints API
- ✅ Schemas validación
- 📝 TODO: Rate limiting
- 📝 TODO: Plantillas HTML email
- 📝 TODO: Retry con backoff exponencial
