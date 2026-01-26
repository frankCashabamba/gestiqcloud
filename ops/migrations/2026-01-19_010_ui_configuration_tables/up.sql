-- Migration: 2026-01-19_010_ui_configuration_tables
-- Description: Create dynamic UI configuration tables (zero hardcodes)
-- Tables: ui_sections, ui_widgets, ui_tables, ui_columns, ui_filters, ui_forms, ui_form_fields, ui_dashboards

BEGIN;

-- ============ UI SECTIONS ============
-- Secciones del dashboard (ej: Dashboard, Pagos, Incidentes)
CREATE TABLE IF NOT EXISTS public.ui_sections (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(100) NOT NULL,
    label VARCHAR(150) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    position INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    show_in_menu BOOLEAN DEFAULT true,
    role_restrictions JSONB,
    module_requirement VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT ui_sections_tenant_slug_unique UNIQUE (tenant_id, slug),
    CONSTRAINT ui_sections_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_sections_tenant_id ON public.ui_sections (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ui_sections_slug ON public.ui_sections (slug);
CREATE INDEX IF NOT EXISTS ix_ui_sections_active ON public.ui_sections (active);

-- ============ UI WIDGETS ============
-- Widgets dinámicos (stat_card, chart, table, form)
CREATE TABLE IF NOT EXISTS public.ui_widgets (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    section_id UUID NOT NULL,
    widget_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    description TEXT,
    position INTEGER DEFAULT 0,
    width INTEGER DEFAULT 100,
    config JSONB NOT NULL,
    api_endpoint VARCHAR(255),
    refresh_interval INTEGER,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT ui_widgets_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE,
    CONSTRAINT ui_widgets_section_fk FOREIGN KEY (section_id) REFERENCES public.ui_sections(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_widgets_tenant_id ON public.ui_widgets (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ui_widgets_section_id ON public.ui_widgets (section_id);
CREATE INDEX IF NOT EXISTS ix_ui_widgets_active ON public.ui_widgets (active);

-- ============ UI TABLES ============
-- Configuración de tablas dinámicas
CREATE TABLE IF NOT EXISTS public.ui_tables (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    api_endpoint VARCHAR(255) NOT NULL,
    model_name VARCHAR(100),
    columns JSONB NOT NULL,
    filters JSONB,
    actions JSONB,
    pagination_size INTEGER DEFAULT 25,
    sortable BOOLEAN DEFAULT true,
    searchable BOOLEAN DEFAULT true,
    exportable BOOLEAN DEFAULT true,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT ui_tables_tenant_slug_unique UNIQUE (tenant_id, slug),
    CONSTRAINT ui_tables_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_tables_tenant_id ON public.ui_tables (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ui_tables_slug ON public.ui_tables (slug);
CREATE INDEX IF NOT EXISTS ix_ui_tables_active ON public.ui_tables (active);

-- ============ UI COLUMNS ============
-- Configuración de columnas de tabla
CREATE TABLE IF NOT EXISTS public.ui_columns (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    label VARCHAR(150) NOT NULL,
    data_type VARCHAR(50) DEFAULT 'string',
    format VARCHAR(100),
    sortable BOOLEAN DEFAULT true,
    filterable BOOLEAN DEFAULT true,
    visible BOOLEAN DEFAULT true,
    position INTEGER DEFAULT 0,
    width INTEGER,
    align VARCHAR(10) DEFAULT 'left',
    CONSTRAINT ui_columns_table_fk FOREIGN KEY (table_id) REFERENCES public.ui_tables(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_columns_table_id ON public.ui_columns (table_id);

-- ============ UI FILTERS ============
-- Configuración de filtros dinámicos
CREATE TABLE IF NOT EXISTS public.ui_filters (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    label VARCHAR(150) NOT NULL,
    filter_type VARCHAR(50) DEFAULT 'text',
    options JSONB,
    default_value VARCHAR(255),
    placeholder VARCHAR(200),
    position INTEGER DEFAULT 0,
    CONSTRAINT ui_filters_table_fk FOREIGN KEY (table_id) REFERENCES public.ui_tables(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_filters_table_id ON public.ui_filters (table_id);

-- ============ UI FORMS ============
-- Formularios dinámicos
CREATE TABLE IF NOT EXISTS public.ui_forms (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    api_endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) DEFAULT 'POST',
    model_name VARCHAR(100),
    fields JSONB NOT NULL,
    submit_button_label VARCHAR(100) DEFAULT 'Guardar',
    success_message VARCHAR(255) DEFAULT 'Guardado exitosamente',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT ui_forms_tenant_slug_unique UNIQUE (tenant_id, slug),
    CONSTRAINT ui_forms_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_forms_tenant_id ON public.ui_forms (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ui_forms_slug ON public.ui_forms (slug);
CREATE INDEX IF NOT EXISTS ix_ui_forms_active ON public.ui_forms (active);

-- ============ UI FORM FIELDS ============
-- Configuración de campos de formulario
CREATE TABLE IF NOT EXISTS public.ui_form_fields (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    label VARCHAR(150) NOT NULL,
    field_type VARCHAR(50) DEFAULT 'text',
    required BOOLEAN DEFAULT false,
    validation JSONB,
    options JSONB,
    placeholder VARCHAR(200),
    help_text VARCHAR(255),
    position INTEGER DEFAULT 0,
    default_value VARCHAR(255),
    CONSTRAINT ui_form_fields_form_fk FOREIGN KEY (form_id) REFERENCES public.ui_forms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_form_fields_form_id ON public.ui_form_fields (form_id);

-- ============ UI DASHBOARDS ============
-- Dashboards personalizados (agrupación de secciones)
CREATE TABLE IF NOT EXISTS public.ui_dashboards (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    slug VARCHAR(100) NOT NULL,
    sections JSONB NOT NULL,
    is_default BOOLEAN DEFAULT false,
    role_visibility JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT ui_dashboards_tenant_slug_unique UNIQUE (tenant_id, slug),
    CONSTRAINT ui_dashboards_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ui_dashboards_tenant_id ON public.ui_dashboards (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ui_dashboards_slug ON public.ui_dashboards (slug);

-- ============ GRANT PERMISSIONS ============
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

COMMIT;
