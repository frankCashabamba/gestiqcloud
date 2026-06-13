# Módulo Suppliers

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Listado, formulario y detalle de proveedores.
- Acciones protegidas por permisos CRUD.

## Parcial

- Datos bancarios y fiscales requieren validación de privacidad.

## Pendiente

- Validar no exposición de IBAN/datos sensibles en listados.
- E2E proveedor -> compra.

## Endpoints usados

- `/api/v1/tenant/suppliers/*`

## Permisos

- `suppliers:read`
- `suppliers:create`
- `suppliers:update`
- `suppliers:delete`

## Tests mínimos

- Crear proveedor.
- Editar proveedor.
- Ver detalle.
- Bloquear eliminación sin permiso.
