-- Corrective migration: ensure overhead_pct exists on recipes
-- Migration 2026-03-08_001 may have been recorded in _migrations without
-- being applied. This migration uses IF NOT EXISTS to remain idempotent.
ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS overhead_pct NUMERIC(5, 2) DEFAULT 5;
