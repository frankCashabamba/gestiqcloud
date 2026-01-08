# Módulo de Producción

## Descripción
Gestión de órdenes de producción y recetas para fabricación de productos.

## Funcionalidades
- **Órdenes de Producción**: Crear, editar, listar y eliminar órdenes
- **Recetas**: Gestionar recetas con ingredientes y rendimientos
- **Estados**: Draft, Scheduled, In Progress, Completed, Cancelled
- **Configuración dinámica**: Campos personalizables desde API

## Endpoints Backend
- `GET /api/v1/production/orders` - Listar órdenes
- `POST /api/v1/production/orders` - Crear orden
- `GET /api/v1/production/orders/:id` - Obtener orden
- `PUT /api/v1/production/orders/:id` - Actualizar orden
- `DELETE /api/v1/production/orders/:id` - Eliminar orden
- `POST /api/v1/production/orders/:id/start` - Iniciar orden
- `POST /api/v1/production/orders/:id/complete` - Completar orden
- `POST /api/v1/production/orders/:id/cancel` - Cancelar orden

## Archivos
- `OrderForm.tsx` - Formulario de órdenes (configuración dinámica)
- `OrdersList.tsx` - Listado con paginación y filtros
- `services.ts` - Tipos TypeScript y funciones API
- `Routes.tsx` - Configuración de rutas
- `manifest.ts` - Metadata del módulo

## Patrón Implementado
Siguiendo el patrón del módulo `clientes`:
- Configuración dinámica desde `/api/v1/company/settings/fields?module=produccion`
- Toast notifications para success/error
- Loading states
- Validación de campos required
- Paginación y ordenamiento en List
- 4 espacios de indentación
- camelCase para funciones/variables
- PascalCase para componentes
