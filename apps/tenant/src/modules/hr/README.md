# Módulo HR

Estado: Activo
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Medio

## Implementado

- Empleados, jornada, fichajes, vacaciones y nómina.
- Rutas protegidas por lectura y gestión.

## Parcial

- Nómina y reglas laborales dependen del país y configuración.

## Pendiente

- Validación legal/fiscal por país.
- E2E empleado -> fichaje -> nómina.

## Endpoints usados

- `/api/v1/tenant/hr/*`

## Permisos

- `hr:read`
- `hr:manage`

## Tests mínimos

- Ver empleados.
- Crear/editar empleado.
- Registrar fichaje.
- Generar nómina de prueba.
