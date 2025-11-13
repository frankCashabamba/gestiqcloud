-- Revertir creación de usuarios_usuarioempresa
-- Migration rollback: 2025-11-01_160_create_usuarios_usuarioempresa

BEGIN;

DROP TABLE IF EXISTS usuarios_usuarioempresa CASCADE;

COMMIT;
