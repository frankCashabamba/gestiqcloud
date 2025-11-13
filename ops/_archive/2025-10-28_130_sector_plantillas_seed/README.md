# Migración: Plantillas de Sector (Seed Data)

## Objetivo
Insertar plantillas predefinidas de configuración para diferentes sectores de negocio.

## Plantillas Incluidas

### 1. Panadería Artesanal
- **Módulos habilitados**: POS, Ventas, Inventario, Facturación, Clientes, Compras, Proveedores, Gastos, Importador, Settings, Usuarios
- **Características**:
  - Tracking de lotes y caducidad
  - Venta por peso habilitada
  - Reorden automático (3 días)
  - Devoluciones: 1 día
  - Color: Café (#8B4513)

### 2. Taller Mecánico
- **Módulos habilitados**: Todos excepto RRHH
- **Características**:
  - Serial tracking para repuestos
  - Precios sin IVA incluido
  - Devoluciones: 30 días
  - Reorden automático (15 días)
  - Color: Rojo (#DC2626)

### 3. Retail / Bazar
- **Módulos habilitados**: Todos
- **Características**:
  - Serial tracking para electrónicos
  - Múltiples categorías
  - Devoluciones: 15 días
  - RRHH habilitado
  - Color: Azul (#5B8CFF)

## Notas
- Los IDs de `tipo_empresa_id` y `tipo_negocio_id` deben ajustarse según los datos existentes
- La migración usa `ON CONFLICT (nombre) DO NOTHING` para evitar duplicados
