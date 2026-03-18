-- ============================================================
-- 2026-03-17_005_user_mfa
-- Tabla para MFA (TOTP) por usuario
-- ============================================================

CREATE TABLE IF NOT EXISTS user_mfa (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES company_users(id) ON DELETE CASCADE,
    totp_secret     VARCHAR(64) NOT NULL,
    is_enabled      BOOLEAN NOT NULL DEFAULT false,
    recovery_codes  TEXT[] NOT NULL DEFAULT '{}',
    backup_email    VARCHAR(255),
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_mfa_user ON user_mfa (user_id);
