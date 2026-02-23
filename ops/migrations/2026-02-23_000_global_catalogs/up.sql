-- Global catalogs for admin-managed reference data
-- These tables have no tenant_id (system-level)

CREATE TABLE IF NOT EXISTS units_of_measure (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expense_categories_global (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    parent_code VARCHAR(20),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_method_templates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed: Units of Measure
INSERT INTO units_of_measure (code, name, abbreviation) VALUES
    ('UN', 'Unidad', 'un'),
    ('KG', 'Kilogramo', 'kg'),
    ('G', 'Gramo', 'g'),
    ('LB', 'Libra', 'lb'),
    ('OZ', 'Onza', 'oz'),
    ('L', 'Litro', 'L'),
    ('ML', 'Mililitro', 'mL'),
    ('M', 'Metro', 'm'),
    ('CM', 'Centímetro', 'cm'),
    ('M2', 'Metro cuadrado', 'm²'),
    ('M3', 'Metro cúbico', 'm³'),
    ('GAL', 'Galón', 'gal'),
    ('CAJA', 'Caja', 'caja'),
    ('PAQUETE', 'Paquete', 'paq'),
    ('DOCENA', 'Docena', 'doc')
ON CONFLICT (code) DO NOTHING;

-- Seed: Document Types
INSERT INTO document_types (code, name, description) VALUES
    ('FAC', 'Factura', 'Factura comercial'),
    ('REC', 'Recibo', 'Recibo de venta / ticket POS'),
    ('NC', 'Nota de crédito', 'Nota de crédito'),
    ('ND', 'Nota de débito', 'Nota de débito'),
    ('GR', 'Guía de remisión', 'Guía de remisión / despacho'),
    ('OC', 'Orden de compra', 'Orden de compra a proveedor'),
    ('COT', 'Cotización', 'Cotización / presupuesto'),
    ('LIQ', 'Liquidación', 'Liquidación de compra')
ON CONFLICT (code) DO NOTHING;

-- Seed: Expense Categories
INSERT INTO expense_categories_global (code, name, parent_code) VALUES
    ('OPS', 'Operaciones', NULL),
    ('OPS-SERV', 'Servicios básicos', 'OPS'),
    ('OPS-ALQ', 'Alquiler', 'OPS'),
    ('OPS-MAN', 'Mantenimiento', 'OPS'),
    ('OPS-SEG', 'Seguros', 'OPS'),
    ('RRHH', 'Recursos humanos', NULL),
    ('RRHH-NOM', 'Nómina', 'RRHH'),
    ('RRHH-CAP', 'Capacitación', 'RRHH'),
    ('MKT', 'Marketing', NULL),
    ('MKT-PUB', 'Publicidad', 'MKT'),
    ('MKT-EVT', 'Eventos', 'MKT'),
    ('TEC', 'Tecnología', NULL),
    ('TEC-SW', 'Software / SaaS', 'TEC'),
    ('TEC-HW', 'Hardware', 'TEC'),
    ('FIN', 'Financieros', NULL),
    ('FIN-INT', 'Intereses', 'FIN'),
    ('FIN-COM', 'Comisiones bancarias', 'FIN'),
    ('OTROS', 'Otros gastos', NULL)
ON CONFLICT (code) DO NOTHING;

-- Seed: Payment Method Templates
INSERT INTO payment_method_templates (code, name, description) VALUES
    ('CASH', 'Efectivo', 'Pago en efectivo'),
    ('CARD', 'Tarjeta', 'Tarjeta de crédito o débito'),
    ('TRANSFER', 'Transferencia', 'Transferencia bancaria'),
    ('CHECK', 'Cheque', 'Pago con cheque'),
    ('CREDIT', 'Crédito', 'Venta a crédito'),
    ('WALLET', 'Billetera digital', 'Pago por billetera electrónica'),
    ('STORE_CREDIT', 'Nota de crédito', 'Pago con nota de crédito de tienda')
ON CONFLICT (code) DO NOTHING;
