-- =====================================================
-- RolEmpresa: Revert column names to Spanish
-- =====================================================
-- Revert English column names back to Spanish in core_rolempresa table

BEGIN;

-- Check if table exists before attempting migration
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'core_rolempresa') THEN
        -- Drop the new unique constraint and restore the old one
        ALTER TABLE core_rolempresa
            DROP CONSTRAINT IF EXISTS uq_empresa_rol;

        -- Rename columns back to Spanish
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'name') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN name TO nombre;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'description') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN description TO descripcion;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'permissions') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN permissions TO permisos;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'created_by_company') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN created_by_company TO creado_por_empresa;
        END IF;

        -- Restore the old unique constraint with the original column name
        ALTER TABLE core_rolempresa
            ADD CONSTRAINT uq_empresa_rol UNIQUE (tenant_id, nombre);
    ELSE
        RAISE NOTICE 'Table core_rolempresa does not exist. Nothing to revert.';
    END IF;
END $$;

COMMIT;
