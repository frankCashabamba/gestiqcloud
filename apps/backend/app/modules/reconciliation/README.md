# Módulo: reconciliation / payments

Propósito: integraciones de pago (Stripe, Payphone, Kushki) y conciliación básica de cobros.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/reconciliation` (montado bajo `/api/v1`).
- Otros flujos de pago pueden estar expuestos desde ventas/POS.

## Componentes clave
- Proveedores en `app/services/payments/{stripe,payphone,kushki}_provider.py`.
- `interface/http` (si aplica) para intents/cobros.

## Notas
- Configurar API keys y endpoints sandbox/producción vía env.
- Validar webhooks si se usan; asegurar seguridad de callbacks.
- Integrado con ventas/POS para generar intents/cargos.
