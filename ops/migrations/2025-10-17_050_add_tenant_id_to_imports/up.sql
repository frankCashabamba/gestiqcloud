-- Migration: Add tenant_id to all imports module tables
-- Description: Tenantize imports module with UUID tenant_id + JSONB conversion + GIN indexes
-- Date: 2025-10-17

-- =====================================================================
-- STEP 1: Add tenant_id columns (nullable initially for backfill)
-- =====================================================================

ALTER TABLE public.import_items ADD COLUMN IF NOT EXISTS tenant_id uuid;
ALTER TABLE public.import_attachments ADD COLUMN IF NOT EXISTS tenant_id uuid;
ALTER TABLE public.import_ocr_jobs ADD COLUMN IF NOT EXISTS tenant_id uuid;

-- Note: import_batches, import_mappings, import_item_corrections, import_lineage already have tenant_id
-- via previous migrations 2025-10-09_016 through 2025-10-09_019

-- =====================================================================
-- STEP 2: Backfill tenant_id from core_empresa.tenant_id via empresa_id
-- =====================================================================

-- import_items: use batch's tenant_id
UPDATE public.import_items i
SET tenant_id = b.tenant_id
FROM public.import_batches b
WHERE i.batch_id = b.id
  AND i.tenant_id IS NULL;

-- import_attachments: use item's tenant_id
UPDATE public.import_attachments a
SET tenant_id = i.tenant_id
FROM public.import_items i
WHERE a.item_id = i.id
  AND a.tenant_id IS NULL;

-- import_ocr_jobs: use empresa_id → tenants mapping
UPDATE public.import_ocr_jobs j
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = j.empresa_id
  AND j.tenant_id IS NULL;

-- =====================================================================
-- STEP 3: Set NOT NULL and create foreign keys
-- =====================================================================

ALTER TABLE public.import_items
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_items_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

ALTER TABLE public.import_attachments
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_attachments_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

ALTER TABLE public.import_ocr_jobs
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_ocr_jobs_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

-- =====================================================================
-- STEP 4: Convert JSON columns to JSONB for better performance
-- =====================================================================

-- import_items
ALTER TABLE public.import_items 
  ALTER COLUMN raw TYPE jsonb USING raw::jsonb,
  ALTER COLUMN normalized TYPE jsonb USING normalized::jsonb,
  ALTER COLUMN errors TYPE jsonb USING errors::jsonb;

-- import_mappings
ALTER TABLE public.import_mappings
  ALTER COLUMN mappings TYPE jsonb USING mappings::jsonb,
  ALTER COLUMN transforms TYPE jsonb USING transforms::jsonb,
  ALTER COLUMN defaults TYPE jsonb USING defaults::jsonb,
  ALTER COLUMN dedupe_keys TYPE jsonb USING dedupe_keys::jsonb;

-- import_ocr_jobs
ALTER TABLE public.import_ocr_jobs
  ALTER COLUMN result TYPE jsonb USING result::jsonb;

-- =====================================================================
-- STEP 5: Create tenant-scoped indexes
-- =====================================================================

-- import_batches (already has tenant_id, add composite index)
CREATE INDEX IF NOT EXISTS ix_import_batches_tenant_status_created 
  ON public.import_batches (tenant_id, status, created_at);

-- import_items
CREATE INDEX IF NOT EXISTS ix_import_items_tenant_id ON public.import_items (tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_items_tenant_dedupe 
  ON public.import_items (tenant_id, dedupe_hash);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS ix_import_items_normalized_gin 
  ON public.import_items USING gin (normalized);
CREATE INDEX IF NOT EXISTS ix_import_items_raw_gin 
  ON public.import_items USING gin (raw);

-- Partial index for doc_type (common filter)
CREATE INDEX IF NOT EXISTS ix_import_items_doc_type 
  ON public.import_items ((normalized->>'doc_type'))
  WHERE normalized ? 'doc_type';

-- import_attachments
CREATE INDEX IF NOT EXISTS ix_import_attachments_tenant_id ON public.import_attachments (tenant_id);

-- import_ocr_jobs
CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_tenant_id ON public.import_ocr_jobs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_tenant_status_created 
  ON public.import_ocr_jobs (tenant_id, status, created_at);

-- import_mappings
CREATE INDEX IF NOT EXISTS ix_import_mappings_tenant_source 
  ON public.import_mappings (tenant_id, source_type);

-- GIN indexes for import_mappings JSONB
CREATE INDEX IF NOT EXISTS ix_import_mappings_mappings_gin 
  ON public.import_mappings USING gin (mappings);

-- =====================================================================
-- STEP 6: Update UNIQUE constraints to be tenant-scoped
-- =====================================================================

-- Drop old constraint and create tenant-scoped one
ALTER TABLE public.import_items 
  DROP CONSTRAINT IF EXISTS uq_import_item_idem;

CREATE UNIQUE INDEX IF NOT EXISTS uq_import_items_tenant_idem 
  ON public.import_items (tenant_id, idempotency_key);

-- =====================================================================
-- STEP 7: Add comments for documentation
-- =====================================================================

COMMENT ON COLUMN public.import_items.tenant_id IS 'Tenant UUID - primary isolation key (empresa_id deprecated)';
COMMENT ON COLUMN public.import_items.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';

COMMENT ON COLUMN public.import_batches.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';

COMMENT ON COLUMN public.import_mappings.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';

COMMENT ON COLUMN public.import_item_corrections.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';

COMMENT ON COLUMN public.import_lineage.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';

COMMENT ON COLUMN public.import_ocr_jobs.empresa_id IS 'DEPRECATED: Will be removed in v2.0. Use tenant_id instead.';
