CREATE TABLE IF NOT EXISTS settings_defaults (
    id SERIAL PRIMARY KEY,
    country VARCHAR(2) NOT NULL,
    name VARCHAR(100) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_settings_defaults_country ON settings_defaults (country);
