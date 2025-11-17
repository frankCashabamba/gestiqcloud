-- Migration: 2025-11-01_165_add_incident_assigned_fk
-- Description: Add foreign key constraint from incidents to company_users
-- This must be done after the company_users table is created

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_incidents_assigned_to'
        AND table_name = 'incidents'
    ) THEN
        ALTER TABLE incidents
        ADD CONSTRAINT fk_incidents_assigned_to
        FOREIGN KEY (assigned_to) REFERENCES company_users(id) ON DELETE SET NULL;
    END IF;
END;
$$;

COMMIT;
