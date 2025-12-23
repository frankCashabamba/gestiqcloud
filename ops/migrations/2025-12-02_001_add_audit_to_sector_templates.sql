-- Migration: Add audit fields to sector_templates for admin UI
-- Date: 2025-12-02
-- Purpose: Track who made changes and config version for admin panel

BEGIN;

-- Add audit columns to sector_templates
ALTER TABLE sector_templates
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS config_version INTEGER DEFAULT 1;

COMMIT;
