# Módulo: admin_config

Propósito: catálogos globales administrados (sectores, tipos de negocio/empresa, países, monedas, timezones, idiomas, plantillas UI, horarios).

## Endpoints
- Admin: `interface/http/admin.py` prefix `/config` montado bajo `/api/v1/admin` → `/api/v1/admin/config`.
- Usado por Admin para configurar catálogos globales.

## Componentes clave
- `application/*`: use cases y DTOs por catálogo (paises, monedas, idiomas, timezones, sectores_plantilla, etc.).
- `infrastructure/*/repository.py`: repositorios por catálogo.
- `crud.py`: operaciones CRUD agrupadas.

## Notas
- Relaciona con `modules/settings` para catálogos y plantillas de UI; settings por tenant viven en `company_settings`.
- Validar dependencias cuando se eliminan catálogos usados por tenants.
