# Módulo: modulos

Propósito: catálogo de módulos disponibles y asignación por tenant/empresa.

## Endpoints
- Tenant: `interface/http/tenant.py` prefix `/modulos`.
- Admin: `interface/http/admin.py` prefix `/admin/modulos` (montado bajo `/api/v1`).
- Público: `interface/http/public.py` prefix `/modulos` (lectura).
- Usado para listar/activar módulos en frontends.

## Componentes clave
- `application/use_cases.py`: lógica de habilitar/deshabilitar módulos y dependencias.
- `application/perm_loader.py`: carga de permisos por módulo.
- `infrastructure/repositories.py`: persistencia y queries.
- `schemas.py`: DTOs y respuestas.

## Notas
- Se integra con settings para reflejar módulos habilitados por tenant.
- Ver catálogos base en `app/modules/settings/application/modules_catalog.py`.
