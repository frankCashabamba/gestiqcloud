-- Revertir columnas de modulos_modulo a español
-- Migration rollback: 2025-11-01_150_modulos_to_english

BEGIN;

-- Revertir nombres de columnas
ALTER TABLE modulos_modulo
    RENAME COLUMN name TO nombre;

ALTER TABLE modulos_modulo
    RENAME COLUMN description TO descripcion;

ALTER TABLE modulos_modulo
    RENAME COLUMN active TO activo;

COMMIT;
