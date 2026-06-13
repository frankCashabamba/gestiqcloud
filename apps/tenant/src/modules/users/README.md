# Módulo Users

Estado: Activo
Madurez: 4/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Gestión de usuarios y roles.
- Permisos granulares para crear, editar, eliminar y cambiar contraseña.

## Parcial

- La coherencia final depende de la matriz de roles y permisos backend.

## Pendiente

- Validar roles operativos mínimos (`admin`, `encargado`, `cajera`, `panadero`).
- E2E usuario sin permiso vs usuario admin.

## Endpoints usados

- `/api/v1/tenant/users/*`
- `/api/v1/tenant/roles/*`

## Permisos

- `users:read`
- `users:create`
- `users:update`
- `users:delete`
- `users:set_password`
- `roles:*`

## Tests mínimos

- Crear usuario.
- Editar usuario.
- Cambiar contraseña.
- Crear rol con permisos.
