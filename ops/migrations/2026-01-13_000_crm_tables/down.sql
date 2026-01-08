-- Migration: 2026-01-13_000_crm_tables
-- Description: Drop CRM tables and enum types.

BEGIN;

DROP TABLE IF EXISTS crm_activities CASCADE;
DROP TABLE IF EXISTS crm_opportunities CASCADE;
DROP TABLE IF EXISTS crm_leads CASCADE;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activitystatus') THEN
        DROP TYPE activitystatus;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activitytype') THEN
        DROP TYPE activitytype;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'opportunitystage') THEN
        DROP TYPE opportunitystage;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadsource') THEN
        DROP TYPE leadsource;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadstatus') THEN
        DROP TYPE leadstatus;
    END IF;
END$$;

COMMIT;
