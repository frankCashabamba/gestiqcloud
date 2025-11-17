-- =====================================================
-- AUTH TABLES: Authentication & Token Management
-- Migration: 2025-11-01_100_auth_tables
-- =====================================================

BEGIN;

-- =====================================================
-- AUTH_USER: Superadmin/System Users
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superadmin BOOLEAN NOT NULL DEFAULT false,
    is_staff BOOLEAN NOT NULL DEFAULT false,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_password_change_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT auth_user_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_auth_user_username ON auth_user(username);
CREATE INDEX IF NOT EXISTS idx_auth_user_email ON auth_user(email);
CREATE INDEX IF NOT EXISTS idx_auth_user_is_active ON auth_user(is_active);

-- =====================================================
-- AUTH_REFRESH_FAMILY: Token Family Management
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_refresh_family (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER,
    tenant_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT auth_refresh_family_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_family_user_id ON auth_refresh_family(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_family_tenant_id ON auth_refresh_family(tenant_id);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_family_revoked_at ON auth_refresh_family(revoked_at);

-- =====================================================
-- AUTH_REFRESH_TOKEN: Individual Refresh Tokens
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_refresh_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES auth_refresh_family(id) ON DELETE CASCADE,
    jti UUID NOT NULL UNIQUE,
    prev_jti UUID,
    ua_hash TEXT,
    ip_hash TEXT,
    token VARCHAR(1000) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT auth_refresh_token_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_family_id ON auth_refresh_token(family_id);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_jti ON auth_refresh_token(jti);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_expires_at ON auth_refresh_token(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_token_revoked_at ON auth_refresh_token(revoked_at);

-- =====================================================
-- AUTH_AUDIT: Audit Trail for Authentication Events
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    username VARCHAR(150),
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON auth_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_username ON auth_audit(username);
CREATE INDEX IF NOT EXISTS idx_auth_audit_event_type ON auth_audit(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_audit_created_at ON auth_audit(created_at);

COMMIT;
