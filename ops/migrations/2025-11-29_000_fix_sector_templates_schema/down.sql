-- Down migration: revert schema changes on sector_templates

-- Drop unique constraint if present
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = 'sector_templates'
          AND constraint_name = 'sector_templates_code_uniq'
    ) THEN
        ALTER TABLE public.sector_templates
        DROP CONSTRAINT sector_templates_code_uniq;
    END IF;
END$$;

-- Switch template_config back to JSON if currently JSONB
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sector_templates'
          AND column_name = 'template_config'
          AND data_type = 'jsonb'
    ) THEN
        ALTER TABLE public.sector_templates
        ALTER COLUMN template_config
        SET DATA TYPE JSON
        USING template_config::json;
    END IF;
END$$;
