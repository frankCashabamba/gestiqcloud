# Módulo Billing

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Listado, formulario y detalle de facturación a clientes.
- Integración con facturación electrónica y export Facturae cuando está disponible.
- Marcado de pago.

## Parcial

- La validez fiscal depende del país, configuración y backend.
- La gestión de planes/suscripciones del tenant vive en Settings, no en este módulo.

## Pendiente

- Validar flujos fiscales EC/ES con sandbox real.
- E2E factura -> e-factura -> estado -> pago.

## Endpoints usados

- `/api/v1/tenant/invoicing/*`
- `/api/v1/tenant/einvoicing/*`

## Permisos

- `billing:read`
- `billing:create`
- `billing:update`
- `billing:delete`
- `billing:send`
- `billing:pay`

## Tests mínimos

- Crear factura.
- Editar factura.
- Enviar e-factura.
- Marcar pagada.
