# Módulo CRM

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Leads y oportunidades.
- Acciones de creación, edición, eliminación y conversión según permisos.

## Parcial

- Pipeline y métricas requieren validación con datos reales.

## Pendiente

- README funcional más detallado por flujo comercial.
- E2E lead -> oportunidad -> venta.

## Endpoints usados

- `/api/v1/tenant/crm/*`

## Permisos

- `crm:read`
- `crm:create`
- `crm:update`
- `crm:delete`
- `crm:manage`

## Tests mínimos

- Crear lead.
- Convertir lead.
- Crear oportunidad.
- Validar botones por permiso.
