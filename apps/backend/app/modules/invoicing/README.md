# Módulo: invoicing

Propósito: facturación (no electrónica) y emisión de documentos.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/facturacion`.
- Admin: `interface/http/admin.py` (si aplica).
- `interface/http/send_email.py`: envío de documentos, prefix `/facturacion`.

## Componentes clave
- `application/use_cases.py`: lógica de emisión.
- `infrastructure/repositories.py`: persistencia.
- `schemas.py`: Pydantic schemas de facturas/líneas.

## Notas
- Plantillas en `app/templates/pdf/` y `app/templates/` para emails.
- Se integra con `einvoicing` para flujos electrónicos específicos.
