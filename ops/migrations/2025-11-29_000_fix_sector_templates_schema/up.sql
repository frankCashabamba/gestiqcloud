-- Migration: Fix sector_templates schema for conflict handling and JSONB ops
-- Purpose:
--  - Enforce uniqueness on code so ON CONFLICT (code) works and prevents duplicates.
--  - Switch template_config to JSONB so jsonb_* functions (jsonb_set, etc.) work.

-- Add unique constraint on sector_templates.code (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema = ccu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = 'sector_templates'
          AND tc.constraint_type = 'UNIQUE'
          AND tc.constraint_name = 'sector_templates_code_uniq'
    ) THEN
        ALTER TABLE public.sector_templates
        ADD CONSTRAINT sector_templates_code_uniq UNIQUE (code);
    END IF;
END$$;

-- Ensure template_config uses JSONB (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sector_templates'
          AND column_name = 'template_config'
          AND data_type <> 'jsonb'
    ) THEN
        ALTER TABLE public.sector_templates
        ALTER COLUMN template_config
        SET DATA TYPE JSONB
        USING template_config::jsonb;
    END IF;
END$$;
