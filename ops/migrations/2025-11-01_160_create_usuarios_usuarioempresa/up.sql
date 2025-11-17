-- Create table usuarios_usuarioempresa for multi-tenant (English columns)
-- Migration: 2025-11-01_160_create_usuarios_usuarioempresa

BEGIN;

CREATE TABLE IF NOT EXISTS usuarios_usuarioempresa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL,
    username VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_company_admin BOOLEAN NOT NULL DEFAULT false,
    password_hash VARCHAR(255) NOT NULL,
    password_token_created TIMESTAMPTZ,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    last_password_change_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_usuarioempresa_tenant_email UNIQUE (tenant_id, email),
    CONSTRAINT uq_usuarioempresa_tenant_username UNIQUE (tenant_id, username)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_usuarioempresa_tenant_id ON usuarios_usuarioempresa(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_usuarioempresa_email ON usuarios_usuarioempresa(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_usuarioempresa_username ON usuarios_usuarioempresa(username);

COMMIT;
