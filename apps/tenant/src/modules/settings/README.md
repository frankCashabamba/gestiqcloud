# Módulo Settings

Estado: Activo
Madurez: 4/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Configuración general, fiscal, branding, horarios, operación, módulos y límites.
- Subrutas embebidas para templates, webhooks, notifications, branches, subscription y security.
- Ruta protegida por `settings:read`.

## Parcial

- Algunas subpantallas usan permisos propios y otras dependen de `settings:read`.
- Configuración avanzada permite JSON técnico; requiere controles de validación.

## Pendiente

- Matriz de permisos por sección.
- E2E settings con usuario permitido/denegado.

## Endpoints usados

- `/api/v1/company/settings/*`
- `/api/v1/tenant/settings/*`
- `/api/v1/tenant/branches/*`
- `/api/v1/tenant/billing/*`

## Permisos

- `settings:read`
- `settings:write`
- Permisos específicos de submódulos.

## Tests mínimos

- Abrir settings.
- Editar configuración básica.
- Acceder a submódulo protegido.
- Bloquear acceso sin permiso.
