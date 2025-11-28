# Módulo: einvoicing

Propósito: facturación electrónica (ej. SRI/Facturae) y envío de comprobantes.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/einvoicing`.

## Componentes clave
- `application/use_cases.py`: lógica de emisión electrónica.
- `services.py`: servicios de integración.
- `schemas.py`: estructuras de comprobantes.
- `tasks.py`: tareas relacionadas.

## Notas
- Configurar credenciales/endpoint del proveedor vía env.
- Validar en sandbox antes de producción; revisar manejo de certificados y numeración.
