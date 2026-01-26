# Módulo de Finanzas

## Descripción
Gestión de caja, bancos y movimientos financieros.

## Funcionalidades
- **Caja**: Movimientos de ingreso/egreso, cierres de caja
- **Bancos**: Movimientos bancarios y conciliación
- **Saldos**: Vista consolidada de saldos
- **Configuración dinámica**: Campos personalizables desde API

## Endpoints Backend
- `GET /api/v1/finanzas/caja` - Listar movimientos de caja
- `POST /api/v1/finanzas/caja` - Crear movimiento de caja
- `GET /api/v1/finanzas/caja/:id` - Obtener movimiento
- `PUT /api/v1/finanzas/caja/:id` - Actualizar movimiento
- `DELETE /api/v1/finanzas/caja/:id` - Eliminar movimiento
- `POST /api/v1/finanzas/caja/cierre` - Registrar cierre de caja
- `GET /api/v1/finanzas/bancos` - Listar movimientos bancarios
- `GET /api/v1/finanzas/saldos` - Obtener saldos consolidados

## Archivos
- `CajaForm.tsx` - Formulario de movimientos (configuración dinámica)
- `CajaList.tsx` - Listado con paginación y filtros
- `CierreCajaModal.tsx` - Modal para cierre de caja
- `BancoList.tsx` - Listado de movimientos bancarios
- `SaldosView.tsx` - Vista de saldos consolidados
- `services.ts` - Tipos TypeScript y funciones API
- `types.ts` - Definiciones de tipos
- `Routes.tsx` - Configuración de rutas
- `manifest.ts` - Metadata del módulo

## Campos Principales Movimiento
- **Identificación**: fecha, tipo (ingreso/egreso), concepto
- **Montos**: monto
- **Clasificación**: categoria, referencia
- **Auditoría**: created_at, updated_at

## Patrón Implementado
Siguiendo el patrón del módulo `clientes`:
- Configuración dinámica desde `/api/v1/company/settings/fields?module=caja`
- Toast notifications para success/error
- Loading states
- Validación de campos required
- Paginación y ordenamiento en List
- 4 espacios de indentación
- camelCase para funciones/variables
- PascalCase para componentes
