# Pagos y Facturacion Electronica

Guia operativa para que un dev pueda modificar/integrar pagos y facturacion electronica sin leer codigo.

## Pagos (detalle)
- Proveedores: Stripe, Payphone, Kushki (implementaciones en `app/services/payments/*_provider.py`).
- Endpoints: expuestos via modulos de ventas/POS o `reconciliation` (`app/modules/reconciliation/interface/http/tenant.py`, prefix `/reconciliation`).
- Entidades: `pos_receipts` (estado), `pos_payments` (registro por pago), conciliacion via `payments`/`facturas`.

### Estados e idempotencia
- `pos_receipts.status`: `draft` -> `paid` -> (opcional) `invoiced`; `voided` para anulaciones.
- `pos_payments`: columnas `method` (`cash|card|store_credit|link`), `amount`, `ref`, `paid_at`; sin estado propio.
- Idempotencia por `receipt_id` (o `payment_intent_id` en metadata). Reintentos deben reutilizar la clave para evitar duplicados.

### Webhooks y callbacks
- URL de callback:
  - Prod: `https://api.gestiqcloud.com/api/v1/reconciliation/link` (pasando por Worker CF si aplica `/api` proxy).
  - Local: exponer via ngrok/tunnel y configurar en el proveedor.
- Stripe: header `Stripe-Signature` (usar `STRIPE_WEBHOOK_SECRET`). Tipos relevantes `payment_intent.succeeded|payment_intent.payment_failed|payment_intent.canceled`. Mapear `metadata.receipt_id` -> recibo. Responder 2xx solo tras persistir.
- Payphone: validar token compartido; `status` `APPROVED|DECLINED|PENDING`; campo `transactionId` como ref; mapear `metadata.receipt_id` si llega.
- Kushki: validar firma/token si aplica; `status` `APPROVED|REJECTED|PENDING`; campo `ticketNumber` como ref.
- Regla de exito: cualquier 2xx. Otros codigos generan reintentos del proveedor; el endpoint debe ser idempotente.

### Flujos base
- Intento de pago: POS crea intencion/cobro -> proveedor -> actualiza `pos_payments` y `pos_receipts.status`.
- Conciliacion: webhook proveedor -> `/reconciliation` -> inserta en `payments` y recalcula `facturas.estado` (`pagada`/`parcial`).

### Env vars
- Stripe: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Payphone: `PAYPHONE_API_KEY`, `PAYPHONE_API_SECRET`, endpoints sandbox/prod.
- Kushki: `KUSHKI_MERCHANT_ID`, `KUSHKI_API_KEY`, `KUSHKI_ENV`.
- Comunes: `PAYMENTS_PROVIDER` (si parametrizamos), dominios de callback por entorno.

### Ejemplos rapidos
- Intent Stripe:
```
{ "amount": 1000, "currency": "usd", "provider": "stripe", "metadata": {"receipt_id": "<uuid>"} }
```
- Webhook Stripe:
```
{ "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123","metadata":{"receipt_id":"<uuid>"},"amount_received":1000}}, "livemode": false }
```
- Payphone request:
```
{ "amount": 1000, "currency": "USD", "provider": "payphone", "metadata": {"receipt_id": "<uuid>"} }
```
- Webhook Payphone:
```
{ "transactionId": "tx_123", "status": "APPROVED", "amount": 1000, "metadata": {"receipt_id": "<uuid>"} }
```
- Kushki request:
```
{ "amount": 1000, "currency": "USD", "provider": "kushki", "metadata": {"receipt_id": "<uuid>"} }
```
- Webhook Kushki:
```
{ "ticketNumber": "TICKET-123", "status": "APPROVED", "amount": 1000, "metadata": {"receipt_id": "<uuid>"} }
```

### Checklist de pruebas
- Caso feliz por proveedor (sandbox), validando actualizacion de `pos_receipts.status`.
- Firma/token invalido en webhook (Stripe Payphone/Kushki) -> debe devolver 400/401 y loggear.
- Idempotencia: mismo `receipt_id` dos veces debe ser noop.
- Payload incompleto o monto distinto -> debe registrarse como error y no duplicar pagos.
- Timeout/destino caido: probar reintentos del proveedor y que el endpoint sea idempotente.

## Facturacion electronica (einvoicing)
- Modulo `app/modules/einvoicing`, endpoints `/api/v1/einvoicing`.
- Servicios en `app/modules/einvoicing/services.py`, tareas en `app/modules/einvoicing/tasks.py`.
- Plantillas/formatos en `app/modules/einvoicing/schemas.py` y `app/templates/pdf/`.

### Estados y modelos
- `sri_submissions.status`: `PENDING|SENT|RECEIVED|AUTHORIZED|REJECTED|ERROR`; campos `error_code`, `error_message`, `authorization_number`.
- `sii_batches.status`: `PENDING|SENT|ACCEPTED|PARTIAL|REJECTED|ERROR`; cada `sii_batch_items.status`: `PENDING|SENT|ACCEPTED|REJECTED|ERROR`.
- Numeracion/series: parametrizable por empresa/tenant (documentar seleccion de serie y secuencia).

### Flujos
- Emision: generar comprobante -> firmar/serializar -> enviar al proveedor -> persistir respuesta -> marcar estado y numero/acuse.
- Consultas: re-verificar estado si quedo en `SENT`/`RECEIVED`.
- Envio por email: `interface/http/send_email.py` (invoicing) para PDF/HTML.
- Reintentos: tasks `sign_and_send` (SRI) y `build_and_send_sii` deben re-ejecutar `status IN ('ERROR','REJECTED')`; `scheduled_retry` automatiza con backoff.

### Env vars
- Credenciales/endpoint del proveedor (SRI/Facturae): URL, API key/certificado, modo sandbox/prod.
- Rutas y passwords de certificados por pais.
- Parametros de numeracion/series y ambiente (`EINVOICING_ENV` si existe).

### Ejemplos
- Emision factura (simplificado):
```
{ "empresa_id": "<tenant_uuid>", "cliente_id": "<uuid>", "items": [ {"sku": "123", "descripcion": "Producto", "cantidad": 1, "precio": 10.0} ], "impuestos": [{"tipo": "IVA", "tasa": 0.12}], "totales": {"subtotal": 10.0, "impuesto": 1.2, "total": 11.2} }
```
- Respuesta proveedor:
```
{ "estado": "autorizado", "numero": "001-001-000000123", "acuse": "...xml...", "mensajes": [] }
```

### Checklist de pruebas
- Emision valida (sandbox) -> estado `AUTHORIZED`/equivalente y numero asignado.
- Simular rechazo/error de validacion -> estado `REJECTED`/`ERROR` con mensaje persistido.
- Reintento desde `ERROR`/`REJECTED` -> debe avanzar o registrar error nuevo, sin duplicar numeracion.
- Verificacion de numeracion/serie correcta por tenant.
- Validar tamaño y tipo de archivos antes de enviar; logs sin datos sensibles (enmascarar).
- Envio email PDF/HTML exitoso y manejo de fallos SMTP.

### Riesgos/puntos de atencion
- Caducidad/clave incorrecta de certificados; validar antes de enviar.
- Latencias altas del proveedor: agregar timeouts y alertas.
- Mantener mapping de estados del proveedor a nuestros modelos documentado y versionado.
