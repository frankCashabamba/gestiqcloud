-- =====================================================
-- Migration: Complete Schema from SQLAlchemy Models
-- Description: Professional consolidated migration
-- Generated: 2025-11-24T11:44:39.089572
-- =====================================================

BEGIN;

-- =====================================================
-- CREATE ENUM TYPES (must come before tables)
-- =====================================================

DROP TYPE IF EXISTS cash_closing_status CASCADE;
CREATE TYPE cash_closing_status AS ENUM ('OPEN', 'CLOSED', 'PENDING');
DROP TYPE IF EXISTS cash_movement_category CASCADE;
CREATE TYPE cash_movement_category AS ENUM ('SALE', 'PURCHASE', 'EXPENSE', 'PAYROLL', 'BANK', 'CHANGE', 'ADJUSTMENT', 'OTHER');
DROP TYPE IF EXISTS cash_movement_type CASCADE;
CREATE TYPE cash_movement_type AS ENUM ('INCOME', 'EXPENSE', 'ADJUSTMENT');
DROP TYPE IF EXISTS payroll_status CASCADE;
CREATE TYPE payroll_status AS ENUM ('DRAFT', 'APPROVED', 'PAID', 'CANCELLED');
DROP TYPE IF EXISTS payroll_type CASCADE;
CREATE TYPE payroll_type AS ENUM ('MONTHLY', 'BONUS', 'SEVERANCE', 'SPECIAL');
DROP TYPE IF EXISTS production_order_status CASCADE;
CREATE TYPE production_order_status AS ENUM ('DRAFT', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
DROP TYPE IF EXISTS transactionstatus CASCADE;
CREATE TYPE transactionstatus AS ENUM ('PENDING', 'RECONCILED', 'REJECTED');
DROP TYPE IF EXISTS transactiontype CASCADE;
CREATE TYPE transactiontype AS ENUM ('RECEIPT', 'TRANSFER', 'CARD', 'CASH', 'OTHER');

-- =====================================================
-- DROP EXISTING TABLES (clean start)
-- =====================================================

DROP TABLE IF EXISTS production_order_lines CASCADE;
DROP TABLE IF EXISTS workshop_lines CASCADE;
DROP TABLE IF EXISTS recipe_ingredients CASCADE;
DROP TABLE IF EXISTS production_orders CASCADE;
DROP TABLE IF EXISTS pos_receipt_lines CASCADE;
DROP TABLE IF EXISTS pos_payments CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS notification_logs CASCADE;
DROP TABLE IF EXISTS internal_transfers CASCADE;
DROP TABLE IF EXISTS bakery_lines CASCADE;
DROP TABLE IF EXISTS store_credit_events CASCADE;
DROP TABLE IF EXISTS stock_alerts CASCADE;
DROP TABLE IF EXISTS recipes CASCADE;
DROP TABLE IF EXISTS purchase_lines CASCADE;
DROP TABLE IF EXISTS payroll_concepts CASCADE;
DROP TABLE IF EXISTS pos_receipts CASCADE;
DROP TABLE IF EXISTS invoice_lines CASCADE;
DROP TABLE IF EXISTS bank_transactions CASCADE;
DROP TABLE IF EXISTS vacations CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS supplier_contacts CASCADE;
DROP TABLE IF EXISTS supplier_addresses CASCADE;
DROP TABLE IF EXISTS store_credits CASCADE;
DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS purchases CASCADE;
DROP TABLE IF EXISTS payrolls CASCADE;
DROP TABLE IF EXISTS payroll_templates CASCADE;
DROP TABLE IF EXISTS cash_movements CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS pos_shifts CASCADE;
DROP TABLE IF EXISTS invoices_temp CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS incidents CASCADE;
DROP TABLE IF EXISTS import_audits CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS doc_series CASCADE;
DROP TABLE IF EXISTS company_user_roles CASCADE;
DROP TABLE IF EXISTS bank_accounts CASCADE;
DROP TABLE IF EXISTS assigned_modules CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS tenant_settings CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS sector_templates CASCADE;
DROP TABLE IF EXISTS cash_closings CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;
DROP TABLE IF EXISTS pos_registers CASCADE;
DROP TABLE IF EXISTS notification_channels CASCADE;
DROP TABLE IF EXISTS inventory_settings CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS company_users CASCADE;
DROP TABLE IF EXISTS company_settings CASCADE;
DROP TABLE IF EXISTS company_roles CASCADE;
DROP TABLE IF EXISTS company_modules CASCADE;
DROP TABLE IF EXISTS company_categories CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS business_types CASCADE;
DROP TABLE IF EXISTS business_hours CASCADE;
DROP TABLE IF EXISTS business_categories CASCADE;
DROP TABLE IF EXISTS bank_movements CASCADE;
DROP TABLE IF EXISTS auth_refresh_token CASCADE;
DROP TABLE IF EXISTS weekdays CASCADE;
DROP TABLE IF EXISTS timezones CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS modules CASCADE;
DROP TABLE IF EXISTS locales CASCADE;
DROP TABLE IF EXISTS languages CASCADE;
DROP TABLE IF EXISTS import_column_mappings CASCADE;
DROP TABLE IF EXISTS global_action_permissions CASCADE;
DROP TABLE IF EXISTS currencies CASCADE;
DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS base_roles CASCADE;
DROP TABLE IF EXISTS auth_user CASCADE;
DROP TABLE IF EXISTS auth_refresh_family CASCADE;
DROP TABLE IF EXISTS auth_audit CASCADE;

-- =====================================================
-- CREATE ALL TABLES
-- =====================================================


CREATE TABLE IF NOT EXISTS auth_audit (
	id UUID NOT NULL,
	kind VARCHAR,
	scope VARCHAR,
	user_id VARCHAR,
	tenant_id VARCHAR,
	ip VARCHAR,
	ua VARCHAR,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS auth_user (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	username VARCHAR(150) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	is_superadmin BOOLEAN DEFAULT false NOT NULL,
	is_staff BOOLEAN DEFAULT false NOT NULL,
	is_verified BOOLEAN DEFAULT false NOT NULL,
	failed_login_count INTEGER DEFAULT 0 NOT NULL,
	locked_until TIMESTAMP WITH TIME ZONE,
	last_login_at TIMESTAMP WITH TIME ZONE,
	last_password_change_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS base_roles (
	id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	permissions JSON NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name)
);


CREATE TABLE IF NOT EXISTS countries (
	id SERIAL NOT NULL,
	code VARCHAR(2) NOT NULL,
	name VARCHAR(100) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
);


CREATE TABLE IF NOT EXISTS currencies (
	id SERIAL NOT NULL,
	code VARCHAR(10) NOT NULL,
	name VARCHAR(100) NOT NULL,
	symbol VARCHAR(5) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
);


CREATE TABLE IF NOT EXISTS global_action_permissions (
	id SERIAL NOT NULL,
	key VARCHAR(100) NOT NULL,
	description VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (key)
);


CREATE TABLE IF NOT EXISTS import_column_mappings (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	name VARCHAR NOT NULL,
	description TEXT,
	file_pattern VARCHAR,
	mapping JSON NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_by UUID,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	last_used_at TIMESTAMP WITHOUT TIME ZONE,
	use_count INTEGER NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS languages (
	id SERIAL NOT NULL,
	code VARCHAR(10) NOT NULL,
	name VARCHAR(100) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
);


CREATE TABLE IF NOT EXISTS locales (
	code VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (code)
);


CREATE TABLE IF NOT EXISTS modules (
	id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	active BOOLEAN NOT NULL,
	icon VARCHAR(100),
	url VARCHAR(255),
	initial_template VARCHAR(255) NOT NULL,
	context_type VARCHAR(10) NOT NULL,
	target_model VARCHAR(255),
	context_filters JSONB,
	category VARCHAR(50),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS tenants (
	id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	slug VARCHAR(100),
	tax_id VARCHAR(30),
	phone VARCHAR(20),
	address TEXT,
	city VARCHAR(100),
	state VARCHAR(100),
	postal_code VARCHAR(20),
	country VARCHAR(100),
	website VARCHAR(255),
	base_currency VARCHAR(3) NOT NULL,
	country_code VARCHAR(2) NOT NULL,
	logo VARCHAR(500),
	primary_color VARCHAR(7) NOT NULL,
	default_template VARCHAR(100) NOT NULL,
	sector_id INTEGER,
	sector_template_name VARCHAR(255),
	config_json JSON,
	active BOOLEAN NOT NULL,
	deactivation_reason TEXT,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS timezones (
	name VARCHAR NOT NULL,
	display_name VARCHAR NOT NULL,
	offset_minutes INTEGER,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (name)
);


CREATE TABLE IF NOT EXISTS weekdays (
	id SERIAL NOT NULL,
	key VARCHAR(20) NOT NULL,
	name VARCHAR(50) NOT NULL,
	"order" INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (key)
);


CREATE TABLE IF NOT EXISTS auth_refresh_family (
	id UUID NOT NULL,
	user_id UUID,
	tenant_id UUID,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS auth_refresh_token (
	id UUID NOT NULL,
	family_id UUID NOT NULL,
	jti UUID NOT NULL,
	prev_jti UUID,
	ua_hash TEXT,
	ip_hash TEXT,
	token VARCHAR,
	expires_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	used_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (token)
);

-- Foreign keys for refresh tokens/families
-- Foreign keys moved after company_users creation

CREATE TABLE IF NOT EXISTS bank_movements (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	account_id UUID,
	date DATE NOT NULL,
	type VARCHAR(10) NOT NULL,
	concept VARCHAR(255) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	previous_balance NUMERIC(12, 2) NOT NULL,
	new_balance NUMERIC(12, 2) NOT NULL,
	bank_reference VARCHAR(100),
	reconciled BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS business_categories (
	id UUID NOT NULL,
	tenant_id UUID,
	code VARCHAR(50),
	name VARCHAR(100) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS business_hours (
	id SERIAL NOT NULL,
	weekday_id INTEGER NOT NULL,
	start_time VARCHAR(5) NOT NULL,
	end_time VARCHAR(5) NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS business_types (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	code VARCHAR(50),
	name VARCHAR(100) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS clients (
	id UUID NOT NULL,
	name VARCHAR NOT NULL,
	tax_id VARCHAR,
	email VARCHAR,
	phone VARCHAR,
	address VARCHAR,
	city VARCHAR,
	state VARCHAR,
	country VARCHAR,
	postal_code VARCHAR,
	tenant_id UUID,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS company_categories (
	id UUID NOT NULL,
	tenant_id UUID,
	code VARCHAR(50),
	name VARCHAR(100) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS company_modules (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	module_id UUID NOT NULL,
	active BOOLEAN NOT NULL,
	activation_date DATE NOT NULL,
	expiration_date DATE,
	initial_template VARCHAR(255),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS company_roles (
	id UUID NOT NULL,
	tenant_id UUID,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	permissions JSON NOT NULL,
	base_role_id UUID,
	created_by_company BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_company_role UNIQUE (tenant_id, name)
);


CREATE TABLE IF NOT EXISTS company_settings (
	id SERIAL NOT NULL,
	tenant_id UUID,
	default_language VARCHAR(10) NOT NULL,
	timezone VARCHAR(50) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	company_logo VARCHAR(100),
	secondary_color VARCHAR(7) NOT NULL,
	primary_color VARCHAR(7) NOT NULL,
	allow_custom_roles BOOLEAN NOT NULL,
	user_limit INTEGER NOT NULL,
	working_days JSON NOT NULL,
	business_hours JSON NOT NULL,
	operation_type VARCHAR NOT NULL,
	company_name VARCHAR,
	tax_id VARCHAR,
	tax_regime VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	language_id INTEGER,
	currency_id INTEGER,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS company_users (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	first_name VARCHAR(100) NOT NULL,
	last_name VARCHAR(100) NOT NULL,
	email VARCHAR(254) NOT NULL,
	username VARCHAR(100) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	is_company_admin BOOLEAN DEFAULT false NOT NULL,
	password_hash VARCHAR NOT NULL,
	password_token_created TIMESTAMP WITH TIME ZONE,
	is_verified BOOLEAN DEFAULT false NOT NULL,
	failed_login_count INTEGER DEFAULT 0 NOT NULL,
	locked_until TIMESTAMP WITH TIME ZONE,
	last_login_at TIMESTAMP WITH TIME ZONE,
	last_password_change_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_company_user_tenant_email UNIQUE (tenant_id, email),
	CONSTRAINT uq_company_user_tenant_username UNIQUE (tenant_id, username)
);


-- Foreign keys for refresh tokens/families (requires company_users to exist)
-- Note: user_id may point to auth_user (admins) or company_users (tenant users), so no FK here
ALTER TABLE auth_refresh_family
    DROP CONSTRAINT IF EXISTS auth_refresh_family_user_id_fkey;

ALTER TABLE auth_refresh_token
    DROP CONSTRAINT IF EXISTS auth_refresh_token_family_id_fkey,
    ADD CONSTRAINT auth_refresh_token_family_fk FOREIGN KEY (family_id) REFERENCES auth_refresh_family(id) ON DELETE CASCADE;


CREATE TABLE IF NOT EXISTS employees (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	user_id UUID,
	code VARCHAR(50),
	first_name VARCHAR(255) NOT NULL,
	last_name VARCHAR(255),
	document VARCHAR(50),
	birth_date DATE,
	hire_date DATE NOT NULL,
	termination_date DATE,
	position VARCHAR(100),
	department VARCHAR(100),
	base_salary NUMERIC(12, 2),
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS inventory_settings (
	id SERIAL NOT NULL,
	tenant_id UUID,
	stock_control_enabled BOOLEAN NOT NULL,
	low_stock_notification_enabled BOOLEAN NOT NULL,
	global_minimum_stock INTEGER,
	default_units JSON,
	custom_categories_enabled BOOLEAN NOT NULL,
	extra_product_fields JSON,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS notification_channels (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	channel_type VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	config JSONB NOT NULL,
	is_active BOOLEAN,
	priority INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_registers (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	store_id UUID,
	name VARCHAR(100) NOT NULL,
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS product_categories (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	name VARCHAR(200) NOT NULL,
	description TEXT,
	parent_id UUID,
	category_metadata JSONB,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.cash_closings (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	date DATE NOT NULL,
	cash_box_id UUID,
	currency VARCHAR(3) NOT NULL,
	opening_balance NUMERIC(12, 2) NOT NULL,
	total_income NUMERIC(12, 2) NOT NULL,
	total_expense NUMERIC(12, 2) NOT NULL,
	theoretical_balance NUMERIC(12, 2) NOT NULL,
	physical_balance NUMERIC(12, 2) NOT NULL,
	difference NUMERIC(12, 2) NOT NULL,
	status cash_closing_status NOT NULL,
	is_balanced BOOLEAN NOT NULL,
	bill_breakdown JSONB,
	notes TEXT,
	opened_by UUID,
	opened_at TIMESTAMP WITH TIME ZONE,
	closed_by UUID,
	closed_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS sector_templates (
	id UUID NOT NULL,
	tenant_id UUID,
	code VARCHAR(50),
	name VARCHAR(100) NOT NULL,
	description TEXT,
	template_config JSON,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS suppliers (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	code VARCHAR(50),
	name VARCHAR(255) NOT NULL,
	trade_name VARCHAR(255),
	tax_id VARCHAR(50),
	email VARCHAR(255),
	phone VARCHAR(50),
	website VARCHAR(255),
	is_active BOOLEAN NOT NULL,
	notes TEXT,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS tenant_settings (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	settings JSONB NOT NULL,
	pos_config JSONB,
	invoice_config JSONB,
	locale VARCHAR(10) NOT NULL,
	timezone VARCHAR(50) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS warehouses (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	code VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	active BOOLEAN NOT NULL,
	metadata JSON,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS assigned_modules (
	id UUID NOT NULL,
	tenant_id UUID,
	user_id UUID NOT NULL,
	module_id UUID NOT NULL,
	assignment_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	auto_view_module BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT assigned_modules_user_id_module_id_tenant_id_uniq UNIQUE (user_id, module_id, tenant_id)
);


CREATE TABLE IF NOT EXISTS bank_accounts (
	id UUID NOT NULL,
	tenant_id UUID,
	name VARCHAR NOT NULL,
	iban VARCHAR NOT NULL,
	bank VARCHAR,
	currency VARCHAR NOT NULL,
	customer_id UUID NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS company_user_roles (
	id SERIAL NOT NULL,
	usuario_id UUID NOT NULL,
	rol_id UUID NOT NULL,
	tenant_id UUID,
	assigned_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	is_active BOOLEAN NOT NULL,
	assigned_by_id UUID,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS doc_series (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	register_id UUID,
	doc_type VARCHAR(10) NOT NULL,
	name VARCHAR(50) NOT NULL,
	current_no INTEGER NOT NULL,
	reset_policy VARCHAR(20) NOT NULL,
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS expenses (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	date DATE NOT NULL,
	concept VARCHAR(255) NOT NULL,
	category VARCHAR(50),
	subcategory VARCHAR(100),
	amount NUMERIC(12, 2) NOT NULL,
	vat NUMERIC(12, 2) NOT NULL,
	total NUMERIC(12, 2) NOT NULL,
	supplier_id UUID,
	payment_method VARCHAR(20),
	invoice_number VARCHAR(100),
	status VARCHAR(20) NOT NULL,
	user_id UUID NOT NULL,
	notes TEXT,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS import_audits (
	id SERIAL NOT NULL,
	document_id INTEGER NOT NULL,
	batch_id UUID,
	item_id UUID,
	tenant_id UUID,
	user_id UUID NOT NULL,
	changes JSONB NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS incidents (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	type VARCHAR(50) NOT NULL,
	severity VARCHAR(20) NOT NULL,
	title VARCHAR(255) NOT NULL,
	description TEXT,
	stack_trace TEXT,
	context JSONB,
	status VARCHAR(20) NOT NULL,
	assigned_to UUID,
	auto_detected BOOLEAN,
	auto_resolved BOOLEAN,
	ia_analysis JSONB,
	ia_suggestion TEXT,
	resolved_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS invoices (
	id UUID NOT NULL,
	number VARCHAR NOT NULL,
	supplier VARCHAR,
	issue_date VARCHAR,
	amount FLOAT NOT NULL,
	status VARCHAR NOT NULL,
	created_at VARCHAR DEFAULT now() NOT NULL,
	tenant_id UUID NOT NULL,
	customer_id UUID NOT NULL,
	subtotal FLOAT NOT NULL,
	vat FLOAT NOT NULL,
	total FLOAT NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS invoices_temp (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	file_name VARCHAR NOT NULL,
	data JSONB NOT NULL,
	status VARCHAR NOT NULL,
	import_date VARCHAR DEFAULT now() NOT NULL,
	tenant_id UUID,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_shifts (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	register_id UUID NOT NULL,
	opened_by UUID NOT NULL,
	opened_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	closed_at TIMESTAMP WITHOUT TIME ZONE,
	opening_float NUMERIC(12, 2) NOT NULL,
	closing_total NUMERIC(12, 2),
	status VARCHAR(20) NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS products (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	sku VARCHAR(100),
	name VARCHAR(255) NOT NULL,
	description TEXT,
	price NUMERIC(12, 2),
	cost_price NUMERIC(12, 2),
	tax_rate NUMERIC(5, 2),
	active BOOLEAN NOT NULL,
	stock FLOAT NOT NULL,
	unit TEXT NOT NULL,
	product_metadata JSON,
	category_id UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.cash_movements (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	type cash_movement_type NOT NULL,
	category cash_movement_category NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	description VARCHAR(255) NOT NULL,
	notes TEXT,
	ref_doc_type VARCHAR(50),
	ref_doc_id UUID,
	cash_box_id UUID,
	user_id UUID,
	date DATE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	closing_id UUID,
	PRIMARY KEY (id),
	FOREIGN KEY(closing_id) REFERENCES public.cash_closings (id) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS public.payroll_templates (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	employee_id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	concepts_json JSONB NOT NULL,
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.payrolls (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	number VARCHAR(50) NOT NULL,
	employee_id UUID NOT NULL,
	period_month INTEGER NOT NULL,
	period_year INTEGER NOT NULL,
	type payroll_type NOT NULL,
	base_salary NUMERIC(12, 2) NOT NULL,
	allowances NUMERIC(12, 2) NOT NULL,
	overtime NUMERIC(12, 2) NOT NULL,
	other_earnings NUMERIC(12, 2) NOT NULL,
	total_earnings NUMERIC(12, 2) NOT NULL,
	social_security NUMERIC(12, 2) NOT NULL,
	income_tax NUMERIC(12, 2) NOT NULL,
	other_deductions NUMERIC(12, 2) NOT NULL,
	total_deductions NUMERIC(12, 2) NOT NULL,
	net_total NUMERIC(12, 2) NOT NULL,
	payment_date DATE,
	payment_method VARCHAR(50),
	status payroll_status NOT NULL,
	notes TEXT,
	concepts_json JSONB,
	approved_by UUID,
	approved_at TIMESTAMP WITH TIME ZONE,
	created_by UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS purchases (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	number VARCHAR(50) NOT NULL,
	supplier_id UUID,
	date DATE NOT NULL,
	subtotal NUMERIC(12, 2) NOT NULL,
	taxes NUMERIC(12, 2) NOT NULL,
	total NUMERIC(12, 2) NOT NULL,
	status VARCHAR(20) NOT NULL,
	notes TEXT,
	delivery_date DATE,
	user_id UUID NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS sales (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	number VARCHAR(50) NOT NULL,
	customer_id UUID,
	date DATE NOT NULL,
	subtotal NUMERIC(12, 2) NOT NULL,
	taxes NUMERIC(12, 2) NOT NULL,
	total NUMERIC(12, 2) NOT NULL,
	status VARCHAR(20) NOT NULL,
	notes TEXT,
	user_id UUID NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);

-- Sales Orders (missing in consolidated schema)
CREATE TABLE IF NOT EXISTS sales_orders (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	number VARCHAR(50) NOT NULL,
	customer_id UUID,
	order_date DATE NOT NULL DEFAULT now(),
	required_date DATE,
	subtotal NUMERIC(12, 2) DEFAULT 0 NOT NULL,
	tax NUMERIC(12, 2) DEFAULT 0 NOT NULL,
	total NUMERIC(12, 2) DEFAULT 0 NOT NULL,
	currency VARCHAR(3) DEFAULT 'EUR',
	status VARCHAR(20) NOT NULL DEFAULT 'draft',
	notes TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (number)
);

CREATE TABLE IF NOT EXISTS sales_order_items (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	sales_order_id UUID NOT NULL,
	product_id UUID NOT NULL,
	quantity NUMERIC(14, 3) NOT NULL,
	unit_price NUMERIC(12, 2) NOT NULL,
	tax_rate NUMERIC(6, 4) DEFAULT 0.21 NOT NULL,
	discount_percent NUMERIC(5, 2) DEFAULT 0 NOT NULL,
	line_total NUMERIC(12, 2) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS store_credits (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	code VARCHAR(50) NOT NULL,
	customer_id UUID,
	currency VARCHAR(3) NOT NULL,
	amount_initial NUMERIC(12, 2) NOT NULL,
	amount_remaining NUMERIC(12, 2) NOT NULL,
	expires_at DATE,
	status VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS supplier_addresses (
	id UUID NOT NULL,
	supplier_id UUID NOT NULL,
	type VARCHAR(20),
	address TEXT,
	city VARCHAR(100),
	state VARCHAR(100),
	postal_code VARCHAR(20),
	country VARCHAR(2) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS supplier_contacts (
	id UUID NOT NULL,
	supplier_id UUID NOT NULL,
	name VARCHAR(255) NOT NULL,
	position VARCHAR(100),
	email VARCHAR(255),
	phone VARCHAR(50),
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS user_profiles (
	id SERIAL NOT NULL,
	user_id UUID NOT NULL,
	language VARCHAR(10) NOT NULL,
	timezone VARCHAR(50) NOT NULL,
	tenant_id UUID,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS vacations (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	employee_id UUID NOT NULL,
	start_date DATE NOT NULL,
	end_date DATE NOT NULL,
	days INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL,
	approved_by UUID,
	notes VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS bank_transactions (
	id UUID NOT NULL,
	tenant_id UUID,
	account_id UUID NOT NULL,
	date DATE NOT NULL,
	amount FLOAT NOT NULL,
	currency VARCHAR NOT NULL,
	type transactiontype NOT NULL,
	status transactionstatus NOT NULL,
	concept VARCHAR NOT NULL,
	reference VARCHAR,
	counterparty_name VARCHAR,
	counterparty_iban VARCHAR,
	counterparty_bank VARCHAR,
	commission FLOAT NOT NULL,
	source VARCHAR NOT NULL,
	attachment_url VARCHAR,
	sepa_end_to_end_id VARCHAR,
	sepa_creditor_id VARCHAR,
	sepa_mandate_ref VARCHAR,
	sepa_scheme VARCHAR,
	customer_id UUID,
	category VARCHAR(100),
	origin VARCHAR(100),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS invoice_lines (
	id UUID NOT NULL,
	invoice_id UUID NOT NULL,
	sector VARCHAR(50) NOT NULL,
	description VARCHAR NOT NULL,
	quantity FLOAT NOT NULL,
	unit_price FLOAT NOT NULL,
	vat FLOAT NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_receipts (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	register_id UUID NOT NULL,
	shift_id UUID NOT NULL,
	number VARCHAR(50) NOT NULL,
	status VARCHAR(20) NOT NULL,
	customer_id UUID,
	invoice_id UUID,
	gross_total NUMERIC(12, 2) NOT NULL,
	tax_total NUMERIC(12, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	paid_at TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.payroll_concepts (
	id UUID NOT NULL,
	payroll_id UUID NOT NULL,
	type VARCHAR(20) NOT NULL,
	code VARCHAR(50) NOT NULL,
	description VARCHAR(255) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	is_base BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(payroll_id) REFERENCES public.payrolls (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS purchase_lines (
	id UUID NOT NULL,
	purchase_id UUID NOT NULL,
	product_id UUID,
	description TEXT,
	quantity NUMERIC(12, 3) NOT NULL,
	unit_price NUMERIC(12, 4) NOT NULL,
	tax_rate NUMERIC(6, 4) NOT NULL,
	total NUMERIC(12, 2) NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS recipes (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID NOT NULL,
	product_id UUID NOT NULL,
	name VARCHAR(200) NOT NULL,
	yield_qty INTEGER NOT NULL,
	total_cost NUMERIC(12, 4),
	unit_cost NUMERIC(12, 4) GENERATED ALWAYS AS (CASE WHEN yield_qty > 0 THEN total_cost / yield_qty ELSE 0 END) STORED,
	prep_time_minutes INTEGER,
	instructions TEXT,
	is_active BOOLEAN,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS stock_alerts (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	product_id UUID NOT NULL,
	warehouse_id UUID,
	alert_type VARCHAR(50) NOT NULL,
	threshold_config JSONB,
	current_qty INTEGER,
	threshold_qty INTEGER,
	status VARCHAR(20) NOT NULL,
	incident_id UUID,
	ia_recommendation TEXT,
	notified_at TIMESTAMP WITH TIME ZONE,
	resolved_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS stock_items (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID,
	warehouse_id UUID NOT NULL,
	product_id UUID NOT NULL,
	qty NUMERIC DEFAULT 0,
	location VARCHAR(50),
	lot VARCHAR(100),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS stock_moves (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	tenant_id UUID,
	product_id UUID NOT NULL,
	warehouse_id UUID NOT NULL,
	qty NUMERIC NOT NULL,
	kind VARCHAR NOT NULL,
	tentative BOOLEAN DEFAULT false NOT NULL,
	posted BOOLEAN DEFAULT false NOT NULL,
	ref_type VARCHAR,
	ref_id VARCHAR,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS store_credit_events (
	id UUID NOT NULL,
	credit_id UUID NOT NULL,
	type VARCHAR(20) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	ref_doc_type VARCHAR(50),
	ref_doc_id UUID,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS bakery_lines (
	id UUID NOT NULL,
	bread_type VARCHAR NOT NULL,
	grams FLOAT NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS internal_transfers (
	id UUID NOT NULL,
	tenant_id UUID,
	source_tx_id UUID NOT NULL,
	destination_tx_id UUID NOT NULL,
	exchange_rate FLOAT NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS notification_logs (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	channel_id UUID,
	incident_id UUID,
	stock_alert_id UUID,
	notification_type VARCHAR(50) NOT NULL,
	recipient VARCHAR(255) NOT NULL,
	subject VARCHAR(255),
	body TEXT,
	status VARCHAR(20) NOT NULL,
	error_message TEXT,
	extra_data JSONB,
	sent_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS payments (
	id UUID NOT NULL,
	tenant_id UUID,
	bank_tx_id UUID NOT NULL,
	invoice_id UUID NOT NULL,
	date DATE NOT NULL,
	applied_amount FLOAT NOT NULL,
	notes VARCHAR,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_payments (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	receipt_id UUID NOT NULL,
	method VARCHAR(20) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	ref TEXT,
	paid_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_receipt_lines (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	receipt_id UUID NOT NULL,
	product_id UUID NOT NULL,
	qty NUMERIC(12, 3) NOT NULL,
	uom VARCHAR(20) NOT NULL,
	unit_price NUMERIC(12, 4) NOT NULL,
	tax_rate NUMERIC(6, 4) NOT NULL,
	discount_pct NUMERIC(5, 2) NOT NULL,
	line_total NUMERIC(12, 2) NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS pos_items (
	id SERIAL NOT NULL,
	receipt_id UUID NOT NULL,
	product_id UUID NOT NULL,
	qty NUMERIC(12, 3) NOT NULL,
	unit_price NUMERIC(12, 4) NOT NULL,
	tax NUMERIC(12, 4) DEFAULT 0 NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.production_orders (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	order_number VARCHAR(50) NOT NULL,
	recipe_id UUID NOT NULL,
	product_id UUID NOT NULL,
	warehouse_id UUID,
	qty_planned NUMERIC(14, 3) NOT NULL,
	qty_produced NUMERIC(14, 3) NOT NULL,
	waste_qty NUMERIC(14, 3) NOT NULL,
	waste_reason TEXT,
	scheduled_date TIMESTAMP WITH TIME ZONE,
	started_at TIMESTAMP WITH TIME ZONE,
	completed_at TIMESTAMP WITH TIME ZONE,
	status production_order_status NOT NULL,
	batch_number VARCHAR(50),
	notes TEXT,
	metadata_json JSONB,
	created_by UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS recipe_ingredients (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	recipe_id UUID NOT NULL,
	product_id UUID NOT NULL,
	qty NUMERIC(12, 4) NOT NULL,
	unit VARCHAR(10) NOT NULL,
	purchase_packaging VARCHAR(100),
	qty_per_package NUMERIC(12, 4) NOT NULL,
	package_unit VARCHAR(10) NOT NULL,
	package_cost NUMERIC(12, 4) NOT NULL,
	ingredient_cost NUMERIC(12, 4) GENERATED ALWAYS AS (CASE WHEN qty_per_package > 0 THEN (qty * package_cost) / qty_per_package ELSE 0 END) STORED,
	notes TEXT,
	line_order INTEGER,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS workshop_lines (
	id UUID NOT NULL,
	spare_part VARCHAR NOT NULL,
	labor_hours FLOAT NOT NULL,
	rate FLOAT NOT NULL,
	PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.production_order_lines (
	id UUID NOT NULL,
	order_id UUID NOT NULL,
	ingredient_product_id UUID NOT NULL,
	stock_move_id UUID,
	qty_required NUMERIC(14, 3) NOT NULL,
	qty_consumed NUMERIC(14, 3) NOT NULL,
	unit VARCHAR(20) NOT NULL,
	cost_unit NUMERIC(12, 4) NOT NULL,
	cost_total NUMERIC(12, 2) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'now()' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(order_id) REFERENCES public.production_orders (id) ON DELETE CASCADE
);

-- =====================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_products_tenant_id ON products(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_categories_tenant_id ON product_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_warehouses_tenant_id ON warehouses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_tenant_id ON stock_alerts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_employees_tenant_id ON employees(tenant_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_tenant_id ON suppliers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_purchases_tenant_id ON purchases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_tenant_id ON sales(tenant_id);
CREATE INDEX IF NOT EXISTS idx_expenses_tenant_id ON expenses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_recipes_tenant_id ON recipes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_production_orders_tenant_id ON production_orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pos_registers_tenant_id ON pos_registers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipts_tenant_id ON pos_receipts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_types_tenant_id ON business_types(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_categories_tenant_id ON business_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_company_categories_tenant_id ON company_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sector_templates_tenant_id ON sector_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_purchase_lines_purchase_id ON purchase_lines(purchase_id);
CREATE INDEX IF NOT EXISTS idx_purchase_lines_product_id ON purchase_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipt_lines_receipt_id ON pos_receipt_lines(receipt_id);
CREATE INDEX IF NOT EXISTS idx_pos_payments_receipt_id ON pos_payments(receipt_id);
CREATE INDEX IF NOT EXISTS idx_payroll_concepts_payroll_id ON payroll_concepts(payroll_id);
CREATE INDEX IF NOT EXISTS idx_production_order_lines_order_id ON production_order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_channel_id ON notification_logs(channel_id);
CREATE INDEX IF NOT EXISTS idx_supplier_addresses_supplier_id ON supplier_addresses(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_contacts_supplier_id ON supplier_contacts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at);

COMMIT;
