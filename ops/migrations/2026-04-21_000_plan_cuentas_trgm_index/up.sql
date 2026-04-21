-- Habilitar extensión pg_trgm si no existe (necesaria para índices GIN trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Índice GIN trigram sobre plan_cuentas.code para acelerar búsquedas ILIKE '%...%'
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_code_trgm
    ON chart_of_accounts USING gin(code gin_trgm_ops);

-- Índice GIN trigram sobre chart_of_accounts.name para acelerar búsquedas ILIKE '%...%'
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_name_trgm
    ON chart_of_accounts USING gin(name gin_trgm_ops);
