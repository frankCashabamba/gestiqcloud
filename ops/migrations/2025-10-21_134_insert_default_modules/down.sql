-- Rollback: Remove default modules
DELETE FROM modulos_modulo WHERE nombre IN (
  'Punto de Venta',
  'Ventas',
  'Inventario',
  'Facturación',
  'Clientes',
  'Proveedores',
  'Contabilidad',
  'Usuarios',
  'Productos',
  'Empresa',
  'Gastos',
  'Finanzas',
  'Importador Excel'
);
