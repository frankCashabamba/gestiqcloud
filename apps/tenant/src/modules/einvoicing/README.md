# Módulo E-invoicing

Estado: Parcial
Madurez: 2/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Dashboard de e-facturación.
- Servicios para envío, estado y reintento.

## Parcial

- Flujo fiscal real depende de certificados, país y homologación.
- SII/SRI/Facturae requieren validación en sandbox.

## Pendiente

- Flujo completo emisión -> firma -> envío -> estado -> descarga.
- Manejo explícito de errores fiscales.

## Endpoints usados

- `/api/v1/tenant/einvoicing/*`

## Permisos

- `einvoicing:read`
- `einvoicing:send`
- `einvoicing:download`
- `einvoicing:retry`

## Tests mínimos

- Ver dashboard.
- Enviar documento en sandbox.
- Reintentar fallo.
- Descargar resultado cuando exista.
