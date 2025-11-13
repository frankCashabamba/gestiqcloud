# Módulo de Nóminas (RRHH)

## Descripción
Gestión de nóminas y recibos de salario para empleados.

## Funcionalidades
- **Nóminas**: Crear, editar, listar y eliminar nóminas
- **Estados**: Draft, Calculated, Approved, Paid, Cancelled
- **Cálculos automáticos**: Total devengado, deducido y líquido
- **Configuración dinámica**: Campos personalizables desde API

## Endpoints Backend
- `GET /api/v1/rrhh/nominas` - Listar nóminas
- `POST /api/v1/rrhh/nominas` - Crear nómina
- `GET /api/v1/rrhh/nominas/:id` - Obtener nómina
- `PUT /api/v1/rrhh/nominas/:id` - Actualizar nómina
- `DELETE /api/v1/rrhh/nominas/:id` - Eliminar nómina
- `POST /api/v1/rrhh/nominas/:id/calculate` - Calcular totales
- `POST /api/v1/rrhh/nominas/:id/approve` - Aprobar nómina
- `POST /api/v1/rrhh/nominas/:id/pay` - Registrar pago

## Archivos
- `NominaForm.tsx` - Formulario de nóminas (configuración dinámica)
- `NominasList.tsx` - Listado con paginación y filtros
- `services/nomina.ts` - Tipos TypeScript y funciones API
- Integrado en `Routes.tsx` existente de RRHH

## Campos Principales
- **Identificación**: numero, empleado_id, periodo (mes/año), tipo
- **Devengos**: salario_base, complementos, horas_extra, otros_devengos
- **Deducciones**: seg_social, irpf, otras_deducciones
- **Totales**: total_devengado, total_deducido, liquido_total
- **Pago**: status, fecha_pago, metodo_pago

## Patrón Implementado
Siguiendo el patrón del módulo `clientes`:
- Configuración dinámica desde `/api/v1/tenant/settings/fields?module=nominas`
- Toast notifications para success/error
- Loading states
- Validación de campos required
- Paginación y ordenamiento en List
- 4 espacios de indentación
- camelCase para funciones/variables
- PascalCase para componentes
