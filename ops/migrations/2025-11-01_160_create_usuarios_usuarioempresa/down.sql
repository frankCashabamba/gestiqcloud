-- Rollback: company_users
-- Migration rollback: 2025-11-01_160_create_usuarios_usuarioempresa

BEGIN;

DROP TABLE IF EXISTS company_users CASCADE;

COMMIT;
