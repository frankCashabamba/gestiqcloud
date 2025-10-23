# 2025-10-21_134_insert_default_modules

## Description
Insert default modules for the MVP. This includes core modules like POS, Ventas, Inventario, etc.

## Changes
- INSERT into `modulos_modulo` table with default modules
- Each module has nombre, descripcion, icono, url, plantilla_inicial, categoria
- Uses ON CONFLICT DO NOTHING to avoid duplicates

## Modules Added
- Punto de Venta (POS)
- Ventas
- Inventario
- Facturación
- Clientes
- Proveedores
- Contabilidad
- Usuarios
- Productos
- Empresa
- Gastos
- Finanzas
- Importador Excel

## Rollback
Removes all inserted modules by nombre.
