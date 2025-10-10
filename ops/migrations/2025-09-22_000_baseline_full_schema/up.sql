-- Generated baseline schema via pg_dump --schema-only --no-owner --no-privileges
-- Cleaned to remove env-specific statements (SET/OWNER/GRANT/etc.)
-- Review before applying in production.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE public.movimientoestado AS ENUM (
    'PENDIENTE',
    'CONCILIADO',
    'RECHAZADO'
);
CREATE TYPE public.movimientotipo AS ENUM (
    'RECIBO',
    'TRANSFERENCIA',
    'TARJETA',
    'EFECTIVO',
    'OTRO'
);
CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);
CREATE TABLE public.auditoria_importacion (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    empresa_id integer NOT NULL,
    usuario_id integer NOT NULL,
    cambios jsonb NOT NULL,
    fecha timestamp without time zone DEFAULT now() NOT NULL,
    batch_id uuid,
    item_id uuid
);
CREATE SEQUENCE public.auditoria_importacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.auth_audit (
    id uuid NOT NULL,
    kind character varying,
    scope character varying,
    user_id character varying,
    tenant_id character varying,
    ip character varying,
    ua character varying,
    created_at timestamp with time zone DEFAULT now()
);
CREATE TABLE public.auth_refresh_family (
    id uuid NOT NULL,
    user_id integer,
    tenant_id uuid,
    created_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone
);
CREATE TABLE public.auth_refresh_token (
    id uuid NOT NULL,
    family_id uuid NOT NULL,
    jti uuid NOT NULL,
    prev_jti uuid,
    used_at timestamp with time zone,
    revoked_at timestamp with time zone,
    ip_hash text,
    created_at timestamp with time zone NOT NULL,
    ua_hash text,
    token character varying,
    expires_at timestamp with time zone
);
CREATE TABLE public.auth_user (
    id integer NOT NULL,
    username character varying NOT NULL,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    is_superadmin boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_staff boolean DEFAULT false NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    tenant_id uuid,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    last_login_at timestamp with time zone,
    last_password_change_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.bank_accounts (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    nombre character varying NOT NULL,
    iban character varying NOT NULL,
    banco character varying,
    moneda character varying NOT NULL,
    cliente_id integer NOT NULL
);
CREATE SEQUENCE public.bank_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.bank_transactions (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    cuenta_id integer NOT NULL,
    fecha date NOT NULL,
    importe double precision NOT NULL,
    moneda character varying NOT NULL,
    tipo public.movimientotipo NOT NULL,
    estado public.movimientoestado NOT NULL,
    concepto character varying NOT NULL,
    referencia character varying,
    contrapartida_nombre character varying,
    contrapartida_iban character varying,
    banco_contraparte character varying,
    comision double precision NOT NULL,
    fuente character varying NOT NULL,
    adjunto_url character varying,
    sepa_end_to_end_id character varying,
    sepa_creditor_id character varying,
    sepa_mandate_ref character varying,
    esquema_sepa character varying,
    categoria character varying(100),
    cliente_id integer,
    origen character varying(100)
);
CREATE SEQUENCE public.bank_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.clients (
    id integer NOT NULL,
    nombre character varying NOT NULL,
    identificacion character varying,
    email character varying,
    telefono character varying,
    direccion character varying,
    localidad character varying,
    provincia character varying,
    pais character varying,
    codigo_postal character varying,
    empresa_id integer NOT NULL
);
CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_categoriaempresa (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL
);
CREATE SEQUENCE public.core_categoriaempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_configuracionempresa (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    idioma_predeterminado character varying(10) NOT NULL,
    zona_horaria character varying(50) NOT NULL,
    moneda character varying(10) NOT NULL,
    logo_empresa character varying(100),
    color_secundario character varying(7) NOT NULL,
    color_primario character varying(7) NOT NULL,
    permitir_roles_personalizados boolean NOT NULL,
    limite_usuarios integer NOT NULL,
    dias_laborales json NOT NULL,
    horario_atencion json NOT NULL,
    tipo_operacion character varying NOT NULL,
    razon_social character varying,
    rfc character varying,
    regimen_fiscal character varying,
    creado_en timestamp without time zone NOT NULL,
    actualizado_en timestamp without time zone NOT NULL,
    idioma_id integer,
    moneda_id integer
);
CREATE SEQUENCE public.core_configuracionempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_configuracioninventarioempresa (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    control_stock_activo boolean NOT NULL,
    notificar_bajo_stock boolean NOT NULL,
    stock_minimo_global integer,
    um_predeterminadas json,
    categorias_personalizadas boolean NOT NULL,
    campos_extra_producto json
);
CREATE SEQUENCE public.core_configuracioninventarioempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_dia (
    id integer NOT NULL,
    clave character varying(20) NOT NULL,
    nombre character varying(50) NOT NULL,
    orden integer NOT NULL
);
CREATE SEQUENCE public.core_dia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_empresa (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    slug character varying(100),
    tipo_empresa_id integer,
    tipo_negocio_id integer,
    ruc character varying(30),
    telefono character varying(20),
    direccion text,
    ciudad character varying(100),
    provincia character varying(100),
    cp character varying(20),
    pais character varying(100),
    logo character varying,
    color_primario character varying(7) NOT NULL,
    activo boolean NOT NULL,
    motivo_desactivacion text,
    plantilla_inicio character varying(100) NOT NULL,
    sitio_web character varying,
    config_json json
);
CREATE SEQUENCE public.core_empresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_horarioatencion (
    id integer NOT NULL,
    dia_id integer NOT NULL,
    inicio character varying(5) NOT NULL,
    fin character varying(5) NOT NULL
);
CREATE SEQUENCE public.core_horarioatencion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_idioma (
    id integer NOT NULL,
    codigo character varying(10) NOT NULL,
    nombre character varying(100) NOT NULL,
    activo boolean NOT NULL
);
CREATE SEQUENCE public.core_idioma_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_moneda (
    id integer NOT NULL,
    codigo character varying(10) NOT NULL,
    nombre character varying(100) NOT NULL,
    simbolo character varying(5) NOT NULL,
    activo boolean NOT NULL
);
CREATE SEQUENCE public.core_moneda_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_perfilusuario (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    idioma character varying(10) NOT NULL,
    zona_horaria character varying(50) NOT NULL,
    empresa_id integer NOT NULL
);
CREATE SEQUENCE public.core_perfilusuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_permisoaccionglobal (
    id integer NOT NULL,
    clave character varying(100) NOT NULL,
    descripcion character varying(100) NOT NULL
);
CREATE SEQUENCE public.core_permisoaccionglobal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_rolbase (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    permisos json NOT NULL
);
CREATE SEQUENCE public.core_rolbase_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_rolempresa (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    permisos json NOT NULL,
    rol_base_id integer,
    creado_por_empresa boolean NOT NULL
);
CREATE SEQUENCE public.core_rolempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_sectorplantilla (
    id integer NOT NULL,
    nombre character varying NOT NULL,
    tipo_empresa_id integer NOT NULL,
    tipo_negocio_id integer NOT NULL,
    config_json json NOT NULL
);
CREATE SEQUENCE public.core_sectorplantilla_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_tipoempresa (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text
);
CREATE SEQUENCE public.core_tipoempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.core_tiponegocio (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text
);
CREATE SEQUENCE public.core_tiponegocio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.datos_importados (
    id integer NOT NULL,
    tipo character varying NOT NULL,
    origen character varying NOT NULL,
    datos json NOT NULL,
    estado character varying NOT NULL,
    empresa_id integer NOT NULL,
    fecha_creacion character varying DEFAULT now() NOT NULL,
    hash character varying NOT NULL
);
CREATE SEQUENCE public.datos_importados_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.facturas (
    id integer NOT NULL,
    numero character varying NOT NULL,
    proveedor character varying NOT NULL,
    fecha_emision character varying NOT NULL,
    monto integer NOT NULL,
    estado character varying NOT NULL,
    fecha_creacion character varying DEFAULT now() NOT NULL,
    empresa_id integer NOT NULL,
    cliente_id integer NOT NULL,
    subtotal double precision NOT NULL,
    iva double precision NOT NULL,
    total double precision NOT NULL
);
CREATE SEQUENCE public.facturas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.facturas_temp (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    archivo_nombre character varying NOT NULL,
    datos jsonb NOT NULL,
    estado character varying NOT NULL,
    fecha_importacion character varying DEFAULT now() NOT NULL,
    empresa_id integer NOT NULL
);
CREATE SEQUENCE public.facturas_temp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.import_batches (
    id uuid NOT NULL,
    empresa_id integer NOT NULL,
    source_type text NOT NULL,
    origin text NOT NULL,
    file_key text,
    mapping_id uuid,
    status text DEFAULT 'PENDING'::text NOT NULL,
    created_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);
CREATE TABLE public.import_item_corrections (
    id uuid NOT NULL,
    empresa_id integer NOT NULL,
    item_id uuid NOT NULL,
    user_id uuid NOT NULL,
    field text NOT NULL,
    old_value jsonb,
    new_value jsonb,
    created_at timestamp with time zone DEFAULT now()
);
CREATE TABLE public.import_items (
    id uuid NOT NULL,
    batch_id uuid NOT NULL,
    idx integer NOT NULL,
    raw jsonb NOT NULL,
    normalized jsonb,
    status text DEFAULT 'PENDING'::text NOT NULL,
    errors jsonb,
    dedupe_hash text,
    idempotency_key text NOT NULL,
    promoted_to text,
    promoted_id uuid,
    promoted_at timestamp with time zone
);
CREATE TABLE public.import_lineage (
    id uuid NOT NULL,
    empresa_id integer NOT NULL,
    item_id uuid NOT NULL,
    promoted_to text NOT NULL,
    promoted_ref text,
    created_at timestamp with time zone DEFAULT now()
);
CREATE TABLE public.import_mappings (
    id uuid NOT NULL,
    empresa_id integer NOT NULL,
    name text NOT NULL,
    source_type text NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    mappings jsonb,
    transforms jsonb,
    defaults jsonb,
    dedupe_keys jsonb,
    created_at timestamp with time zone DEFAULT now()
);
-- Attachments for imported items (photos/files, optional OCR)
CREATE TABLE public.import_attachments (
    id uuid NOT NULL,
    item_id uuid NOT NULL,
    kind character varying NOT NULL,
    file_key character varying NOT NULL,
    sha256 character varying,
    ocr_text text,
    created_at timestamp with time zone DEFAULT now()
);
CREATE TABLE public.internal_transfers (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    tx_origen_id integer NOT NULL,
    tx_destino_id integer NOT NULL,
    cambio double precision NOT NULL
);
CREATE SEQUENCE public.internal_transfers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.invoice_line (
    id integer NOT NULL,
    factura_id integer NOT NULL,
    descripcion character varying NOT NULL,
    cantidad double precision NOT NULL,
    precio_unitario double precision NOT NULL,
    iva double precision NOT NULL,
    sector character varying(50) NOT NULL
);
CREATE SEQUENCE public.invoice_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.lineas_panaderia (
    id integer NOT NULL,
    tipo_pan character varying NOT NULL,
    gramos double precision NOT NULL
);
CREATE TABLE public.lineas_taller (
    id integer NOT NULL,
    repuesto character varying NOT NULL,
    horas_mano_obra double precision NOT NULL,
    tarifa double precision NOT NULL
);
CREATE TABLE public.modulos_empresamodulo (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    modulo_id integer NOT NULL,
    activo boolean NOT NULL,
    fecha_activacion date NOT NULL,
    fecha_expiracion date,
    plantilla_inicial character varying(255)
);
CREATE SEQUENCE public.modulos_empresamodulo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.modulos_modulo (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    activo boolean NOT NULL,
    icono character varying(100),
    url character varying(255),
    plantilla_inicial character varying(255) NOT NULL,
    context_type character varying(10) NOT NULL,
    modelo_objetivo character varying(255),
    filtros_contexto jsonb,
    categoria character varying(50)
);
CREATE SEQUENCE public.modulos_modulo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.modulos_moduloasignado (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    usuario_id integer NOT NULL,
    modulo_id integer NOT NULL,
    fecha_asignacion timestamp without time zone NOT NULL,
    ver_modulo_auto boolean NOT NULL
);
CREATE SEQUENCE public.modulos_moduloasignado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.payments (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    bank_tx_id integer NOT NULL,
    factura_id integer NOT NULL,
    fecha date NOT NULL,
    importe_aplicado double precision NOT NULL,
    notas character varying
);
CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.products (
    id integer NOT NULL,
    name character varying NOT NULL,
    price double precision NOT NULL,
    stock double precision NOT NULL,
    unit character varying NOT NULL,
    product_metadata json,
    empresa_id integer NOT NULL
);
CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.recipe_ingredients (
    id integer NOT NULL,
    recipe_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity double precision NOT NULL,
    unit character varying NOT NULL
);
CREATE SEQUENCE public.recipe_ingredients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.recipes (
    id integer NOT NULL,
    product_id integer NOT NULL,
    yield_quantity double precision NOT NULL
);
CREATE SEQUENCE public.recipes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.usuarios_usuarioempresa (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    nombre_encargado character varying(100) NOT NULL,
    apellido_encargado character varying(100) NOT NULL,
    email character varying NOT NULL,
    username character varying(100) NOT NULL,
    activo boolean NOT NULL,
    es_admin_empresa boolean NOT NULL,
    password_hash character varying NOT NULL,
    password_token_created timestamp without time zone,
    is_verified boolean DEFAULT false NOT NULL,
    tenant_id uuid,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    last_login_at timestamp with time zone,
    last_password_change_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
CREATE SEQUENCE public.usuarios_usuarioempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.usuarios_usuariorolempresa (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    rol_id integer NOT NULL,
    empresa_id integer NOT NULL,
    fecha_asignacion timestamp without time zone DEFAULT now() NOT NULL,
    activo boolean NOT NULL,
    asignado_por_id integer
);
CREATE SEQUENCE public.usuarios_usuariorolempresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE ONLY public.alembic_version ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);
ALTER TABLE ONLY public.auditoria_importacion ADD CONSTRAINT auditoria_importacion_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_audit ADD CONSTRAINT auth_audit_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_refresh_family ADD CONSTRAINT auth_refresh_family_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_refresh_token ADD CONSTRAINT auth_refresh_token_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_refresh_token ADD CONSTRAINT auth_refresh_token_token_key UNIQUE (token);
ALTER TABLE ONLY public.auth_user ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.bank_accounts ADD CONSTRAINT bank_accounts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.bank_transactions ADD CONSTRAINT bank_transactions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.clients ADD CONSTRAINT clients_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_categoriaempresa ADD CONSTRAINT core_categoriaempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_configuracionempresa ADD CONSTRAINT core_configuracionempresa_empresa_id_key UNIQUE (empresa_id);
ALTER TABLE ONLY public.core_configuracionempresa ADD CONSTRAINT core_configuracionempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_configuracioninventarioempresa ADD CONSTRAINT core_configuracioninventarioempresa_empresa_id_key UNIQUE (empresa_id);
ALTER TABLE ONLY public.core_configuracioninventarioempresa ADD CONSTRAINT core_configuracioninventarioempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_dia ADD CONSTRAINT core_dia_clave_key UNIQUE (clave);
ALTER TABLE ONLY public.core_dia ADD CONSTRAINT core_dia_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_empresa ADD CONSTRAINT core_empresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_empresa ADD CONSTRAINT core_empresa_slug_key UNIQUE (slug);
ALTER TABLE ONLY public.core_horarioatencion ADD CONSTRAINT core_horarioatencion_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_idioma ADD CONSTRAINT core_idioma_codigo_key UNIQUE (codigo);
ALTER TABLE ONLY public.core_idioma ADD CONSTRAINT core_idioma_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_moneda ADD CONSTRAINT core_moneda_codigo_key UNIQUE (codigo);
ALTER TABLE ONLY public.core_moneda ADD CONSTRAINT core_moneda_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_perfilusuario ADD CONSTRAINT core_perfilusuario_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_permisoaccionglobal ADD CONSTRAINT core_permisoaccionglobal_clave_key UNIQUE (clave);
ALTER TABLE ONLY public.core_permisoaccionglobal ADD CONSTRAINT core_permisoaccionglobal_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_rolbase ADD CONSTRAINT core_rolbase_nombre_key UNIQUE (nombre);
ALTER TABLE ONLY public.core_rolbase ADD CONSTRAINT core_rolbase_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_rolempresa ADD CONSTRAINT core_rolempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_sectorplantilla ADD CONSTRAINT core_sectorplantilla_nombre_key UNIQUE (nombre);
ALTER TABLE ONLY public.core_sectorplantilla ADD CONSTRAINT core_sectorplantilla_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_tipoempresa ADD CONSTRAINT core_tipoempresa_nombre_key UNIQUE (nombre);
ALTER TABLE ONLY public.core_tipoempresa ADD CONSTRAINT core_tipoempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.core_tiponegocio ADD CONSTRAINT core_tiponegocio_nombre_key UNIQUE (nombre);
ALTER TABLE ONLY public.core_tiponegocio ADD CONSTRAINT core_tiponegocio_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.datos_importados ADD CONSTRAINT datos_importados_hash_key UNIQUE (hash);
ALTER TABLE ONLY public.datos_importados ADD CONSTRAINT datos_importados_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.facturas ADD CONSTRAINT facturas_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.facturas_temp ADD CONSTRAINT facturas_temp_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_batches ADD CONSTRAINT import_batches_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_item_corrections ADD CONSTRAINT import_item_corrections_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_items ADD CONSTRAINT import_items_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_lineage ADD CONSTRAINT import_lineage_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_mappings ADD CONSTRAINT import_mappings_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.import_attachments ADD CONSTRAINT import_attachments_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.internal_transfers ADD CONSTRAINT internal_transfers_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.invoice_line ADD CONSTRAINT invoice_line_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.lineas_panaderia ADD CONSTRAINT lineas_panaderia_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.lineas_taller ADD CONSTRAINT lineas_taller_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.modulos_empresamodulo ADD CONSTRAINT modulos_empresamodulo_empresa_id_modulo_id_uniq UNIQUE (empresa_id, modulo_id);
ALTER TABLE ONLY public.modulos_empresamodulo ADD CONSTRAINT modulos_empresamodulo_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.modulos_modulo ADD CONSTRAINT modulos_modulo_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.modulos_moduloasignado ADD CONSTRAINT modulos_moduloasignado_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.modulos_moduloasignado ADD CONSTRAINT modulos_moduloasignado_usuario_id_modulo_id_empresa_id_uniq UNIQUE (usuario_id, modulo_id, empresa_id);
ALTER TABLE ONLY public.payments ADD CONSTRAINT payments_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.products ADD CONSTRAINT products_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.recipe_ingredients ADD CONSTRAINT recipe_ingredients_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.recipes ADD CONSTRAINT recipes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.bank_accounts ADD CONSTRAINT uq_empresa_rol UNIQUE (empresa_id, nombre);
ALTER TABLE ONLY public.datos_importados ADD CONSTRAINT uq_hash_documento UNIQUE (hash);
ALTER TABLE ONLY public.usuarios_usuarioempresa ADD CONSTRAINT usuarios_usuarioempresa_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.usuarios_usuarioempresa ADD CONSTRAINT usuarios_usuarioempresa_username_key UNIQUE (username);
ALTER TABLE ONLY public.usuarios_usuariorolempresa ADD CONSTRAINT usuarios_usuariorolempresa_pkey PRIMARY KEY (id);
CREATE INDEX ix_auditoria_importacion_documento_id ON public.auditoria_importacion USING btree (documento_id);
CREATE INDEX ix_auditoria_importacion_id ON public.auditoria_importacion USING btree (id);
CREATE INDEX ix_auth_audit_kind ON public.auth_audit USING btree (kind);
CREATE INDEX ix_auth_audit_scope ON public.auth_audit USING btree (scope);
CREATE INDEX ix_auth_audit_tenant_id ON public.auth_audit USING btree (tenant_id);
CREATE INDEX ix_auth_audit_user_id ON public.auth_audit USING btree (user_id);
CREATE INDEX ix_auth_refresh_family_revoked_at ON public.auth_refresh_family USING btree (revoked_at);
CREATE INDEX ix_auth_refresh_family_tenant_id ON public.auth_refresh_family USING btree (tenant_id);
CREATE INDEX ix_auth_refresh_family_user_id ON public.auth_refresh_family USING btree (user_id);
CREATE INDEX ix_auth_refresh_token_expires_at ON public.auth_refresh_token USING btree (expires_at);
CREATE INDEX ix_auth_refresh_token_family_id ON public.auth_refresh_token USING btree (family_id);
CREATE UNIQUE INDEX ix_auth_refresh_token_jti ON public.auth_refresh_token USING btree (jti);
CREATE INDEX ix_auth_refresh_token_prev_jti ON public.auth_refresh_token USING btree (prev_jti);
CREATE UNIQUE INDEX ix_auth_user_email ON public.auth_user USING btree (email);
CREATE INDEX ix_auth_user_id ON public.auth_user USING btree (id);
CREATE INDEX ix_auth_user_tenant_id ON public.auth_user USING btree (tenant_id);
CREATE UNIQUE INDEX ix_auth_user_username ON public.auth_user USING btree (username);
CREATE INDEX ix_bank_accounts_empresa_id ON public.bank_accounts USING btree (empresa_id);
CREATE INDEX ix_bank_accounts_iban ON public.bank_accounts USING btree (iban);
CREATE INDEX ix_bank_transactions_cuenta_id ON public.bank_transactions USING btree (cuenta_id);
CREATE INDEX ix_bank_transactions_empresa_id ON public.bank_transactions USING btree (empresa_id);
CREATE INDEX ix_bank_transactions_fecha ON public.bank_transactions USING btree (fecha);
CREATE INDEX ix_clients_id ON public.clients USING btree (id);
CREATE INDEX ix_core_configuracionempresa_id ON public.core_configuracionempresa USING btree (id);
CREATE INDEX ix_core_configuracioninventarioempresa_id ON public.core_configuracioninventarioempresa USING btree (id);
CREATE INDEX ix_datos_importados_id ON public.datos_importados USING btree (id);
CREATE INDEX ix_facturas_id ON public.facturas USING btree (id);
CREATE INDEX ix_facturas_temp_id ON public.facturas_temp USING btree (id);
CREATE INDEX ix_import_items_batch ON public.import_items USING btree (batch_id);
CREATE INDEX ix_import_items_dedupe ON public.import_items USING btree (dedupe_hash);
CREATE INDEX ix_import_attachments_item ON public.import_attachments USING btree (item_id);
CREATE INDEX ix_internal_transfers_empresa_id ON public.internal_transfers USING btree (empresa_id);
CREATE INDEX ix_modulos_empresamodulo_id ON public.modulos_empresamodulo USING btree (id);
CREATE INDEX ix_modulos_modulo_id ON public.modulos_modulo USING btree (id);
CREATE INDEX ix_payments_bank_tx_id ON public.payments USING btree (bank_tx_id);
CREATE INDEX ix_payments_empresa_id ON public.payments USING btree (empresa_id);
CREATE INDEX ix_payments_factura_id ON public.payments USING btree (factura_id);
CREATE INDEX ix_products_id ON public.products USING btree (id);
CREATE INDEX ix_products_name ON public.products USING btree (name);
CREATE INDEX ix_recipe_ingredients_id ON public.recipe_ingredients USING btree (id);
CREATE INDEX ix_recipes_id ON public.recipes USING btree (id);
CREATE UNIQUE INDEX ix_usuarios_usuarioempresa_email ON public.usuarios_usuarioempresa USING btree (email);
CREATE INDEX ix_usuarios_usuarioempresa_id ON public.usuarios_usuarioempresa USING btree (id);
CREATE INDEX ix_usuarios_usuarioempresa_tenant_id ON public.usuarios_usuarioempresa USING btree (tenant_id);
CREATE INDEX ix_usuarios_usuariorolempresa_id ON public.usuarios_usuariorolempresa USING btree (id);
CREATE UNIQUE INDEX uq_import_item_idem ON public.import_items USING btree (idempotency_key);
ALTER TABLE ONLY public.auditoria_importacion ADD CONSTRAINT auditoria_importacion_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.auditoria_importacion ADD CONSTRAINT auditoria_importacion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios_usuarioempresa(id);
ALTER TABLE ONLY public.auth_refresh_token ADD CONSTRAINT auth_refresh_token_family_id_fkey FOREIGN KEY (family_id) REFERENCES public.auth_refresh_family(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.bank_accounts ADD CONSTRAINT bank_accounts_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clients(id);
ALTER TABLE ONLY public.bank_accounts ADD CONSTRAINT bank_accounts_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.bank_transactions ADD CONSTRAINT bank_transactions_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clients(id);
ALTER TABLE ONLY public.bank_transactions ADD CONSTRAINT bank_transactions_cuenta_id_fkey FOREIGN KEY (cuenta_id) REFERENCES public.bank_accounts(id);
ALTER TABLE ONLY public.bank_transactions ADD CONSTRAINT bank_transactions_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.clients ADD CONSTRAINT clients_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.core_configuracionempresa ADD CONSTRAINT core_configuracionempresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.core_configuracionempresa ADD CONSTRAINT core_configuracionempresa_idioma_id_fkey FOREIGN KEY (idioma_id) REFERENCES public.core_idioma(id);
ALTER TABLE ONLY public.core_configuracionempresa ADD CONSTRAINT core_configuracionempresa_moneda_id_fkey FOREIGN KEY (moneda_id) REFERENCES public.core_moneda(id);
ALTER TABLE ONLY public.core_configuracioninventarioempresa ADD CONSTRAINT core_configuracioninventarioempresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.core_empresa ADD CONSTRAINT core_empresa_tipo_empresa_id_fkey FOREIGN KEY (tipo_empresa_id) REFERENCES public.core_tipoempresa(id);
ALTER TABLE ONLY public.core_empresa ADD CONSTRAINT core_empresa_tipo_negocio_id_fkey FOREIGN KEY (tipo_negocio_id) REFERENCES public.core_tiponegocio(id);
ALTER TABLE ONLY public.core_horarioatencion ADD CONSTRAINT core_horarioatencion_dia_id_fkey FOREIGN KEY (dia_id) REFERENCES public.core_dia(id);
ALTER TABLE ONLY public.core_perfilusuario ADD CONSTRAINT core_perfilusuario_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.core_perfilusuario ADD CONSTRAINT core_perfilusuario_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios_usuarioempresa(id);
ALTER TABLE ONLY public.core_rolempresa ADD CONSTRAINT core_rolempresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.core_rolempresa ADD CONSTRAINT core_rolempresa_rol_base_id_fkey FOREIGN KEY (rol_base_id) REFERENCES public.core_rolbase(id);
ALTER TABLE ONLY public.core_sectorplantilla ADD CONSTRAINT core_sectorplantilla_tipo_empresa_id_fkey FOREIGN KEY (tipo_empresa_id) REFERENCES public.core_tipoempresa(id);
ALTER TABLE ONLY public.core_sectorplantilla ADD CONSTRAINT core_sectorplantilla_tipo_negocio_id_fkey FOREIGN KEY (tipo_negocio_id) REFERENCES public.core_tiponegocio(id);
ALTER TABLE ONLY public.datos_importados ADD CONSTRAINT datos_importados_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.facturas ADD CONSTRAINT facturas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clients(id);
ALTER TABLE ONLY public.facturas ADD CONSTRAINT facturas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.facturas_temp ADD CONSTRAINT facturas_temp_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.facturas_temp ADD CONSTRAINT facturas_temp_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios_usuarioempresa(id);
ALTER TABLE ONLY public.import_batches ADD CONSTRAINT import_batches_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.import_item_corrections ADD CONSTRAINT import_item_corrections_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.import_item_corrections ADD CONSTRAINT import_item_corrections_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.import_items(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.import_items ADD CONSTRAINT import_items_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.import_lineage ADD CONSTRAINT import_lineage_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.import_lineage ADD CONSTRAINT import_lineage_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.import_items(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.import_mappings ADD CONSTRAINT import_mappings_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.import_attachments ADD CONSTRAINT import_attachments_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.import_items(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.internal_transfers ADD CONSTRAINT internal_transfers_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.internal_transfers ADD CONSTRAINT internal_transfers_tx_destino_id_fkey FOREIGN KEY (tx_destino_id) REFERENCES public.bank_transactions(id);
ALTER TABLE ONLY public.internal_transfers ADD CONSTRAINT internal_transfers_tx_origen_id_fkey FOREIGN KEY (tx_origen_id) REFERENCES public.bank_transactions(id);
ALTER TABLE ONLY public.invoice_line ADD CONSTRAINT invoice_line_factura_id_fkey FOREIGN KEY (factura_id) REFERENCES public.facturas(id);
ALTER TABLE ONLY public.lineas_panaderia ADD CONSTRAINT lineas_panaderia_id_fkey FOREIGN KEY (id) REFERENCES public.invoice_line(id);
ALTER TABLE ONLY public.lineas_taller ADD CONSTRAINT lineas_taller_id_fkey FOREIGN KEY (id) REFERENCES public.invoice_line(id);
ALTER TABLE ONLY public.modulos_empresamodulo ADD CONSTRAINT modulos_empresamodulo_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.modulos_empresamodulo ADD CONSTRAINT modulos_empresamodulo_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos_modulo(id);
ALTER TABLE ONLY public.modulos_moduloasignado ADD CONSTRAINT modulos_moduloasignado_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.modulos_moduloasignado ADD CONSTRAINT modulos_moduloasignado_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos_modulo(id);
ALTER TABLE ONLY public.modulos_moduloasignado ADD CONSTRAINT modulos_moduloasignado_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios_usuarioempresa(id);
ALTER TABLE ONLY public.payments ADD CONSTRAINT payments_bank_tx_id_fkey FOREIGN KEY (bank_tx_id) REFERENCES public.bank_transactions(id);
ALTER TABLE ONLY public.payments ADD CONSTRAINT payments_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.payments ADD CONSTRAINT payments_factura_id_fkey FOREIGN KEY (factura_id) REFERENCES public.facturas(id);
ALTER TABLE ONLY public.products ADD CONSTRAINT products_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.recipe_ingredients ADD CONSTRAINT recipe_ingredients_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);
ALTER TABLE ONLY public.recipe_ingredients ADD CONSTRAINT recipe_ingredients_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(id);
ALTER TABLE ONLY public.recipes ADD CONSTRAINT recipes_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);
ALTER TABLE ONLY public.usuarios_usuarioempresa ADD CONSTRAINT usuarios_usuarioempresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.usuarios_usuariorolempresa ADD CONSTRAINT usuarios_usuariorolempresa_asignado_por_id_fkey FOREIGN KEY (asignado_por_id) REFERENCES public.usuarios_usuarioempresa(id);
ALTER TABLE ONLY public.usuarios_usuariorolempresa ADD CONSTRAINT usuarios_usuariorolempresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.core_empresa(id);
ALTER TABLE ONLY public.usuarios_usuariorolempresa ADD CONSTRAINT usuarios_usuariorolempresa_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.core_rolempresa(id);
ALTER TABLE ONLY public.usuarios_usuariorolempresa ADD CONSTRAINT usuarios_usuariorolempresa_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios_usuarioempresa(id);
