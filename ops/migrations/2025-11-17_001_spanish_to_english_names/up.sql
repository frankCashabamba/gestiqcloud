-- =====================================================
-- MIGRACION: Español → Inglés (Spanish to English)
-- Estandarización de nombres de tablas y columnas
-- =====================================================

BEGIN;

-- =====================================================
-- SUPPLIERS (was proveedores)
-- =====================================================
ALTER TABLE IF EXISTS proveedores RENAME TO suppliers;
ALTER TABLE IF EXISTS supplier_contacts RENAME COLUMN proveedor_id TO supplier_id;
ALTER TABLE IF EXISTS supplier_addresses RENAME COLUMN proveedor_id TO supplier_id;

-- Renombrar columnas en suppliers
ALTER TABLE suppliers RENAME COLUMN codigo TO code;
ALTER TABLE suppliers RENAME COLUMN nombre TO name;
ALTER TABLE suppliers RENAME COLUMN nombre_comercial TO trade_name;
ALTER TABLE suppliers RENAME COLUMN telefono TO phone;
ALTER TABLE suppliers RENAME COLUMN web TO website;
ALTER TABLE suppliers RENAME COLUMN activo TO is_active;
ALTER TABLE suppliers RENAME COLUMN notas TO notes;

-- Renombrar tablas relacionadas
ALTER TABLE IF EXISTS proveedor_contactos RENAME TO supplier_contacts;
ALTER TABLE IF EXISTS proveedor_direcciones RENAME TO supplier_addresses;

-- Renombrar columnas en supplier_contacts
ALTER TABLE supplier_contacts RENAME COLUMN nombre TO name;
ALTER TABLE supplier_contacts RENAME COLUMN cargo TO position;
ALTER TABLE supplier_contacts RENAME COLUMN telefono TO phone;
ALTER TABLE supplier_contacts RENAME COLUMN supplier_id TO supplier_id;  -- ya cambió con FK

-- Renombrar columnas en supplier_addresses
ALTER TABLE supplier_addresses RENAME COLUMN tipo TO type;
ALTER TABLE supplier_addresses RENAME COLUMN direccion TO address;
ALTER TABLE supplier_addresses RENAME COLUMN ciudad TO city;
ALTER TABLE supplier_addresses RENAME COLUMN provincia TO state;
ALTER TABLE supplier_addresses RENAME COLUMN codigo_postal TO postal_code;
ALTER TABLE supplier_addresses RENAME COLUMN pais TO country;

-- =====================================================
-- SALES (was ventas)
-- =====================================================
ALTER TABLE IF EXISTS ventas RENAME TO sales;
ALTER TABLE sales RENAME COLUMN numero TO number;
ALTER TABLE sales RENAME COLUMN cliente_id TO customer_id;
ALTER TABLE sales RENAME COLUMN fecha TO date;
ALTER TABLE sales RENAME COLUMN impuestos TO taxes;
ALTER TABLE sales RENAME COLUMN estado TO status;
ALTER TABLE sales RENAME COLUMN notas TO notes;
ALTER TABLE sales RENAME COLUMN usuario_id TO user_id;

-- =====================================================
-- PURCHASES (was compras)
-- =====================================================
ALTER TABLE IF EXISTS compras RENAME TO purchases;
ALTER TABLE purchases RENAME COLUMN numero TO number;
ALTER TABLE purchases RENAME COLUMN proveedor_id TO supplier_id;
ALTER TABLE purchases RENAME COLUMN fecha TO date;
ALTER TABLE purchases RENAME COLUMN impuestos TO taxes;
ALTER TABLE purchases RENAME COLUMN estado TO status;
ALTER TABLE purchases RENAME COLUMN notas TO notes;
ALTER TABLE purchases RENAME COLUMN fecha_entrega TO delivery_date;
ALTER TABLE purchases RENAME COLUMN usuario_id TO user_id;

ALTER TABLE IF EXISTS compra_lineas RENAME TO purchase_lines;
ALTER TABLE purchase_lines RENAME COLUMN compra_id TO purchase_id;
ALTER TABLE purchase_lines RENAME COLUMN producto_id TO product_id;
ALTER TABLE purchase_lines RENAME COLUMN descripcion TO description;
ALTER TABLE purchase_lines RENAME COLUMN cantidad TO quantity;
ALTER TABLE purchase_lines RENAME COLUMN precio_unitario TO unit_price;
ALTER TABLE purchase_lines RENAME COLUMN impuesto_tasa TO tax_rate;

-- =====================================================
-- EXPENSES (was gastos)
-- =====================================================
ALTER TABLE IF EXISTS gastos RENAME TO expenses;
ALTER TABLE expenses RENAME COLUMN concepto TO concept;
ALTER TABLE expenses RENAME COLUMN categoria TO category;
ALTER TABLE expenses RENAME COLUMN subcategoria TO subcategory;
ALTER TABLE expenses RENAME COLUMN cantidad TO amount;
ALTER TABLE expenses RENAME COLUMN iva TO vat;
ALTER TABLE expenses RENAME COLUMN metodo_pago TO payment_method;
ALTER TABLE expenses RENAME COLUMN numero_factura TO invoice_number;

-- =====================================================
-- FINANCE (banco_movimientos)
-- =====================================================
ALTER TABLE IF EXISTS banco_movimientos RENAME TO bank_movements;
ALTER TABLE bank_movements RENAME COLUMN cuenta_id TO account_id;
ALTER TABLE bank_movements RENAME COLUMN tipo TO type;
ALTER TABLE bank_movements RENAME COLUMN concepto TO concept;
ALTER TABLE bank_movements RENAME COLUMN cantidad TO amount;
ALTER TABLE bank_movements RENAME COLUMN saldo_anterior TO previous_balance;
ALTER TABLE bank_movements RENAME COLUMN saldo_nuevo TO new_balance;
ALTER TABLE bank_movements RENAME COLUMN referencia_banco TO bank_reference;
ALTER TABLE bank_movements RENAME COLUMN conciliado TO reconciled;

-- =====================================================
-- HR: PAYROLL (was nominas)
-- =====================================================
ALTER TABLE IF EXISTS nominas RENAME TO payrolls;
ALTER TABLE payrolls RENAME COLUMN numero TO number;
ALTER TABLE payrolls RENAME COLUMN usuario_id TO user_id;
ALTER TABLE payrolls RENAME COLUMN fecha_inicio TO start_date;
ALTER TABLE payrolls RENAME COLUMN fecha_fin TO end_date;
ALTER TABLE payrolls RENAME COLUMN estado TO status;
ALTER TABLE payrolls RENAME COLUMN periodo_mes TO period_month;
ALTER TABLE payrolls RENAME COLUMN periodo_ano TO period_year;
ALTER TABLE payrolls RENAME COLUMN tipo TO type;
ALTER TABLE payrolls RENAME COLUMN salario_base TO base_salary;
ALTER TABLE payrolls RENAME COLUMN complementos TO allowances;
ALTER TABLE payrolls RENAME COLUMN horas_extra TO overtime;
ALTER TABLE payrolls RENAME COLUMN otros_devengos TO other_earnings;
ALTER TABLE payrolls RENAME COLUMN total_devengado TO total_earnings;
ALTER TABLE payrolls RENAME COLUMN seg_social TO social_security;
ALTER TABLE payrolls RENAME COLUMN irpf TO income_tax;
ALTER TABLE payrolls RENAME COLUMN otras_deducciones TO other_deductions;
ALTER TABLE payrolls RENAME COLUMN total_deducido TO total_deductions;
ALTER TABLE payrolls RENAME COLUMN fecha_pago TO payment_date;
ALTER TABLE payrolls RENAME COLUMN metodo_pago TO payment_method;
ALTER TABLE payrolls RENAME COLUMN notas TO notes;
ALTER TABLE payrolls RENAME COLUMN conceptos_json TO concepts_json;
ALTER TABLE payrolls RENAME COLUMN aprobado_por TO approved_by;
ALTER TABLE payrolls RENAME COLUMN aprobado_en TO approved_at;
ALTER TABLE payrolls RENAME COLUMN creado_por TO created_by;

ALTER TABLE IF EXISTS nomina_conceptos RENAME TO payroll_items;
ALTER TABLE payroll_items RENAME COLUMN nomina_id TO payroll_id;
ALTER TABLE payroll_items RENAME COLUMN tipo TO type;
ALTER TABLE payroll_items RENAME COLUMN codigo TO code;
ALTER TABLE payroll_items RENAME COLUMN descripcion TO description;
ALTER TABLE payroll_items RENAME COLUMN importe TO amount;
ALTER TABLE payroll_items RENAME COLUMN es_base TO is_base;

ALTER TABLE IF EXISTS nomina_plantillas RENAME TO payroll_templates;
ALTER TABLE payroll_templates RENAME COLUMN empleado_id TO employee_id;
ALTER TABLE payroll_templates RENAME COLUMN nombre TO name;
ALTER TABLE payroll_templates RENAME COLUMN descripcion TO description;
ALTER TABLE payroll_templates RENAME COLUMN conceptos_json TO concepts_json;
ALTER TABLE payroll_templates RENAME COLUMN activo TO is_active;

-- =====================================================
-- IMPORTS & AUDIT
-- =====================================================
ALTER TABLE IF EXISTS auditoria_importacion RENAME TO import_audit;

-- =====================================================
-- INVOICE LINES
-- =====================================================
ALTER TABLE IF EXISTS lineas_panaderia RENAME TO bakery_lines;
ALTER TABLE IF EXISTS lineas_taller RENAME TO workshop_lines;
ALTER TABLE IF EXISTS facturas_temp RENAME TO invoices_temp;

-- =====================================================
-- MODULES (Core Modules)
-- =====================================================
ALTER TABLE IF EXISTS modulos_modulo RENAME TO modules;
ALTER TABLE IF EXISTS modulos_empresamodulo RENAME TO company_modules;
ALTER TABLE IF EXISTS modulos_moduloasignado RENAME TO assigned_modules;

-- =====================================================
-- COMPANY (Empresa)
-- =====================================================
ALTER TABLE IF EXISTS usuarios_usuariorolempresa RENAME TO user_company_roles;
ALTER TABLE IF EXISTS usuarios_usuarioempresa RENAME TO user_companies;
ALTER TABLE IF EXISTS core_configuracionempresa RENAME TO company_settings;
ALTER TABLE IF EXISTS core_configuracioninventarioempresa RENAME TO company_inventory_settings;
ALTER TABLE IF EXISTS core_rolempresa RENAME TO company_roles;
ALTER TABLE IF EXISTS core_tipoempresa RENAME TO company_types;
ALTER TABLE IF EXISTS core_tiponegocio RENAME TO business_types;
ALTER TABLE IF EXISTS core_moneda RENAME TO currencies_legacy;

-- =====================================================
-- RECREATE FOREIGN KEY CONSTRAINTS
-- =====================================================

-- Update FK in sales (was ventas)
ALTER TABLE sales DROP CONSTRAINT IF EXISTS ventas_proveedor_id_fkey;
ALTER TABLE sales ADD CONSTRAINT sales_customer_id_fkey
    FOREIGN KEY (customer_id) REFERENCES clients(id) ON DELETE SET NULL;

-- Update FK in purchases (was compras)
ALTER TABLE purchases DROP CONSTRAINT IF EXISTS compras_proveedor_id_fkey;
ALTER TABLE purchases ADD CONSTRAINT purchases_supplier_id_fkey
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL;

-- Update FK in purchase_lines (was compra_lineas)
ALTER TABLE purchase_lines DROP CONSTRAINT IF EXISTS compra_lineas_compra_id_fkey;
ALTER TABLE purchase_lines DROP CONSTRAINT IF EXISTS compra_lineas_producto_id_fkey;
ALTER TABLE purchase_lines ADD CONSTRAINT purchase_lines_purchase_id_fkey
    FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE;
ALTER TABLE purchase_lines ADD CONSTRAINT purchase_lines_product_id_fkey
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL;

COMMIT;
