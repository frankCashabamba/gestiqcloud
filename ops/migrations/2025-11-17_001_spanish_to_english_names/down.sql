-- =====================================================
-- MIGRACION REVERTIDA: Inglés → Español
-- =====================================================

BEGIN;

-- =====================================================
-- SUPPLIERS back to PROVEEDORES
-- =====================================================
ALTER TABLE suppliers RENAME COLUMN code TO codigo;
ALTER TABLE suppliers RENAME COLUMN name TO nombre;
ALTER TABLE suppliers RENAME COLUMN trade_name TO nombre_comercial;
ALTER TABLE suppliers RENAME COLUMN phone TO telefono;
ALTER TABLE suppliers RENAME COLUMN website TO web;
ALTER TABLE suppliers RENAME COLUMN is_active TO activo;
ALTER TABLE suppliers RENAME COLUMN notes TO notas;

ALTER TABLE suppliers RENAME TO proveedores;
ALTER TABLE supplier_contacts RENAME TO proveedor_contactos;
ALTER TABLE supplier_addresses RENAME TO proveedor_direcciones;

ALTER TABLE proveedor_contactos RENAME COLUMN name TO nombre;
ALTER TABLE proveedor_contactos RENAME COLUMN position TO cargo;
ALTER TABLE proveedor_contactos RENAME COLUMN phone TO telefono;
ALTER TABLE proveedor_contactos RENAME COLUMN supplier_id TO proveedor_id;

ALTER TABLE proveedor_direcciones RENAME COLUMN type TO tipo;
ALTER TABLE proveedor_direcciones RENAME COLUMN address TO direccion;
ALTER TABLE proveedor_direcciones RENAME COLUMN city TO ciudad;
ALTER TABLE proveedor_direcciones RENAME COLUMN state TO provincia;
ALTER TABLE proveedor_direcciones RENAME COLUMN postal_code TO codigo_postal;
ALTER TABLE proveedor_direcciones RENAME COLUMN country TO pais;

-- =====================================================
-- SALES back to VENTAS
-- =====================================================
ALTER TABLE sales RENAME COLUMN number TO numero;
ALTER TABLE sales RENAME COLUMN customer_id TO cliente_id;
ALTER TABLE sales RENAME COLUMN date TO fecha;
ALTER TABLE sales RENAME COLUMN taxes TO impuestos;
ALTER TABLE sales RENAME COLUMN status TO estado;
ALTER TABLE sales RENAME COLUMN notes TO notas;
ALTER TABLE sales RENAME COLUMN user_id TO usuario_id;

ALTER TABLE sales RENAME TO ventas;

-- =====================================================
-- PURCHASES back to COMPRAS
-- =====================================================
ALTER TABLE purchases RENAME COLUMN number TO numero;
ALTER TABLE purchases RENAME COLUMN supplier_id TO proveedor_id;
ALTER TABLE purchases RENAME COLUMN date TO fecha;
ALTER TABLE purchases RENAME COLUMN taxes TO impuestos;
ALTER TABLE purchases RENAME COLUMN status TO estado;
ALTER TABLE purchases RENAME COLUMN notes TO notas;
ALTER TABLE purchases RENAME COLUMN delivery_date TO fecha_entrega;
ALTER TABLE purchases RENAME COLUMN user_id TO usuario_id;

ALTER TABLE purchases RENAME TO compras;

ALTER TABLE purchase_lines RENAME COLUMN purchase_id TO compra_id;
ALTER TABLE purchase_lines RENAME COLUMN product_id TO producto_id;
ALTER TABLE purchase_lines RENAME COLUMN description TO descripcion;
ALTER TABLE purchase_lines RENAME COLUMN quantity TO cantidad;
ALTER TABLE purchase_lines RENAME COLUMN unit_price TO precio_unitario;
ALTER TABLE purchase_lines RENAME COLUMN tax_rate TO impuesto_tasa;

ALTER TABLE purchase_lines RENAME TO compra_lineas;

-- =====================================================
-- EXPENSES back to GASTOS
-- =====================================================
ALTER TABLE expenses RENAME TO gastos;

-- =====================================================
-- FINANCE back
-- =====================================================
ALTER TABLE bank_movements RENAME TO banco_movimientos;

-- =====================================================
-- HR: PAYROLL back to NOMINAS
-- =====================================================
ALTER TABLE payrolls RENAME COLUMN number TO numero;
ALTER TABLE payrolls RENAME COLUMN user_id TO usuario_id;
ALTER TABLE payrolls RENAME COLUMN start_date TO fecha_inicio;
ALTER TABLE payrolls RENAME COLUMN end_date TO fecha_fin;
ALTER TABLE payrolls RENAME COLUMN status TO estado;

ALTER TABLE payrolls RENAME TO nominas;
ALTER TABLE payroll_items RENAME TO nomina_conceptos;
ALTER TABLE payroll_templates RENAME TO nomina_plantillas;

-- =====================================================
-- IMPORTS & AUDIT back
-- =====================================================
ALTER TABLE import_audit RENAME TO auditoria_importacion;

-- =====================================================
-- INVOICE LINES back
-- =====================================================
ALTER TABLE bakery_lines RENAME TO lineas_panaderia;
ALTER TABLE workshop_lines RENAME TO lineas_taller;
ALTER TABLE invoices_temp RENAME TO facturas_temp;

-- =====================================================
-- MODULES back
-- =====================================================
ALTER TABLE modules RENAME TO modulos_modulo;
ALTER TABLE company_modules RENAME TO modulos_empresamodulo;
ALTER TABLE assigned_modules RENAME TO modulos_moduloasignado;

-- =====================================================
-- COMPANY back
-- =====================================================
ALTER TABLE user_company_roles RENAME TO usuarios_usuariorolempresa;
ALTER TABLE user_companies RENAME TO usuarios_usuarioempresa;
ALTER TABLE company_settings RENAME TO core_configuracionempresa;
ALTER TABLE company_inventory_settings RENAME TO core_configuracioninventarioempresa;
ALTER TABLE company_roles RENAME TO core_rolempresa;
ALTER TABLE company_types RENAME TO core_tipoempresa;
ALTER TABLE business_types RENAME TO core_tiponegocio;
ALTER TABLE currencies_legacy RENAME TO core_moneda;

COMMIT;
