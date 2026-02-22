-- Migration: 2026-02-22_002_recipe_steps_table
-- Description: Create recipe_steps table for detailed step-by-step recipe costing.

BEGIN;

CREATE TABLE IF NOT EXISTS recipe_steps (
    id                UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id         UUID            NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_name         VARCHAR(100)    NOT NULL,
    description       TEXT            NULL,
    duration_minutes  INTEGER         NOT NULL DEFAULT 0,
    is_touch          BOOLEAN         NOT NULL DEFAULT TRUE,
    resource_type     VARCHAR(20)     NOT NULL DEFAULT 'labor',
    actual_minutes    INTEGER         NULL,
    step_order        INTEGER         NOT NULL DEFAULT 0,
    is_active         BOOLEAN         DEFAULT TRUE,
    created_at        TIMESTAMPTZ     DEFAULT now(),
    updated_at        TIMESTAMPTZ     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe_id     ON recipe_steps (recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_is_touch      ON recipe_steps (is_touch);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_resource_type ON recipe_steps (resource_type);

COMMIT;
