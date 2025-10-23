-- Insert default modules for MVP
-- This migration adds basic modules like POS, Ventas, Inventario, etc.

-- Ensure unique constraint on nombre
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'modulos_modulo_nombre_unique'
    ) THEN
        ALTER TABLE modulos_modulo ADD CONSTRAINT modulos_modulo_nombre_unique UNIQUE (nombre);
    END IF;
END $$;

INSERT INTO modulos_modulo (nombre, descripcion, activo, icono, url, plantilla_inicial, context_type, modelo_objetivo, categoria)
VALUES
  ('Punto de Venta', 'Módulo de Punto de Venta para ventas en mostrador', true, '🛒', '/pos', 'panaderia', 'none', NULL, 'Ventas'),
  ('Ventas', 'Gestión de ventas y entregas', true, '📊', '/ventas', 'panaderia', 'none', NULL, 'Ventas'),
  ('Inventario', 'Control de stock y productos', true, '📦', '/inventario', 'panaderia', 'none', NULL, 'Inventario'),
  ('Facturación', 'Emisión y gestión de facturas', true, '📄', '/facturacion', 'panaderia', 'none', NULL, 'Contabilidad'),
  ('Clientes', 'Base de datos de clientes', true, '👥', '/clientes', 'panaderia', 'none', NULL, 'CRM'),
  ('Proveedores', 'Gestión de proveedores', true, '🏢', '/proveedores', 'panaderia', 'none', NULL, 'Compras'),
  ('Contabilidad', 'Registros contables', true, '💼', '/contabilidad', 'panaderia', 'none', NULL, 'Contabilidad'),
  ('Usuarios', 'Gestión de usuarios y roles', true, '👤', '/usuarios', 'panaderia', 'none', NULL, 'Admin'),
  ('Productos', 'Catálogo de productos', true, '🏷️', '/productos', 'panaderia', 'none', NULL, 'Inventario'),
  ('Empresa', 'Configuración de la empresa', true, '🏢', '/empresa', 'panaderia', 'none', NULL, 'Admin'),
  ('Gastos', 'Registro de gastos', true, '💰', '/gastos', 'panaderia', 'none', NULL, 'Contabilidad'),
  ('Finanzas', 'Dashboard financiero', true, '📈', '/finanzas', 'panaderia', 'none', NULL, 'Contabilidad'),
  ('Importador Excel', 'Importación masiva desde Excel', true, '📥', '/importador-excel', 'panaderia', 'none', NULL, 'Admin')
ON CONFLICT (nombre) DO NOTHING;
