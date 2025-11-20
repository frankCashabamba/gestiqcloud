-- =====================================================
-- RolEmpresa: Rename columns to English
-- =====================================================
-- Rename Spanish column names to English in core_rolempresa table
-- This migration assumes the table already exists from ORM schema generation
-- Renames: nombre -> name, descripcion -> description,
--          permisos -> permissions, creado_por_empresa -> created_by_company

BEGIN;

-- Check if table exists before attempting migration
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'core_rolempresa') THEN
        -- Rename columns only if they exist
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'nombre') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN nombre TO name;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'descripcion') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN descripcion TO description;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'permisos') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN permisos TO permissions;
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_rolempresa' AND column_name = 'creado_por_empresa') THEN
            ALTER TABLE core_rolempresa RENAME COLUMN creado_por_empresa TO created_by_company;
        END IF;

        -- Drop the old unique constraint and create a new one with the renamed column
        ALTER TABLE core_rolempresa
            DROP CONSTRAINT IF EXISTS uq_empresa_rol;

        ALTER TABLE core_rolempresa
            ADD CONSTRAINT uq_empresa_rol UNIQUE (tenant_id, name);
    ELSE
        RAISE NOTICE 'Table core_rolempresa does not exist yet. It will be created by ORM schema generation.';
    END IF;
END $$;

COMMIT;
