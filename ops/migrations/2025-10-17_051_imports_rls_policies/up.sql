-- =====================================================================
-- RLS Policies for Imports Module (tenant_id UUID)
-- =====================================================================
-- Naming convention: p_{table}_tenant_{action}
-- GUC variable: app.tenant_id (UUID)
-- =====================================================================

-- ===== import_batches =====
ALTER TABLE public.import_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_batches FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_batches_tenant_select ON public.import_batches;
CREATE POLICY p_import_batches_tenant_select
  ON public.import_batches
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_batches_tenant_insert ON public.import_batches;
CREATE POLICY p_import_batches_tenant_insert
  ON public.import_batches
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_batches_tenant_update ON public.import_batches;
CREATE POLICY p_import_batches_tenant_update
  ON public.import_batches
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_batches_tenant_delete ON public.import_batches;
CREATE POLICY p_import_batches_tenant_delete
  ON public.import_batches
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_items =====
ALTER TABLE public.import_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_items FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_items_tenant_select ON public.import_items;
CREATE POLICY p_import_items_tenant_select
  ON public.import_items
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_items_tenant_insert ON public.import_items;
CREATE POLICY p_import_items_tenant_insert
  ON public.import_items
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_items_tenant_update ON public.import_items;
CREATE POLICY p_import_items_tenant_update
  ON public.import_items
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_items_tenant_delete ON public.import_items;
CREATE POLICY p_import_items_tenant_delete
  ON public.import_items
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_mappings =====
ALTER TABLE public.import_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_mappings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_mappings_tenant_select ON public.import_mappings;
CREATE POLICY p_import_mappings_tenant_select
  ON public.import_mappings
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_mappings_tenant_insert ON public.import_mappings;
CREATE POLICY p_import_mappings_tenant_insert
  ON public.import_mappings
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_mappings_tenant_update ON public.import_mappings;
CREATE POLICY p_import_mappings_tenant_update
  ON public.import_mappings
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_mappings_tenant_delete ON public.import_mappings;
CREATE POLICY p_import_mappings_tenant_delete
  ON public.import_mappings
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_item_corrections =====
ALTER TABLE public.import_item_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_item_corrections FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_item_corrections_tenant_select ON public.import_item_corrections;
CREATE POLICY p_import_item_corrections_tenant_select
  ON public.import_item_corrections
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_item_corrections_tenant_insert ON public.import_item_corrections;
CREATE POLICY p_import_item_corrections_tenant_insert
  ON public.import_item_corrections
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_item_corrections_tenant_update ON public.import_item_corrections;
CREATE POLICY p_import_item_corrections_tenant_update
  ON public.import_item_corrections
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_item_corrections_tenant_delete ON public.import_item_corrections;
CREATE POLICY p_import_item_corrections_tenant_delete
  ON public.import_item_corrections
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_lineage =====
ALTER TABLE public.import_lineage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_lineage FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_lineage_tenant_select ON public.import_lineage;
CREATE POLICY p_import_lineage_tenant_select
  ON public.import_lineage
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_lineage_tenant_insert ON public.import_lineage;
CREATE POLICY p_import_lineage_tenant_insert
  ON public.import_lineage
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_lineage_tenant_update ON public.import_lineage;
CREATE POLICY p_import_lineage_tenant_update
  ON public.import_lineage
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_lineage_tenant_delete ON public.import_lineage;
CREATE POLICY p_import_lineage_tenant_delete
  ON public.import_lineage
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_attachments =====
ALTER TABLE public.import_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_attachments FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_attachments_tenant_select ON public.import_attachments;
CREATE POLICY p_import_attachments_tenant_select
  ON public.import_attachments
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_attachments_tenant_insert ON public.import_attachments;
CREATE POLICY p_import_attachments_tenant_insert
  ON public.import_attachments
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_attachments_tenant_update ON public.import_attachments;
CREATE POLICY p_import_attachments_tenant_update
  ON public.import_attachments
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_attachments_tenant_delete ON public.import_attachments;
CREATE POLICY p_import_attachments_tenant_delete
  ON public.import_attachments
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ===== import_ocr_jobs =====
ALTER TABLE public.import_ocr_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_ocr_jobs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_select ON public.import_ocr_jobs;
CREATE POLICY p_import_ocr_jobs_tenant_select
  ON public.import_ocr_jobs
  FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_insert ON public.import_ocr_jobs;
CREATE POLICY p_import_ocr_jobs_tenant_insert
  ON public.import_ocr_jobs
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_update ON public.import_ocr_jobs;
CREATE POLICY p_import_ocr_jobs_tenant_update
  ON public.import_ocr_jobs
  FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_delete ON public.import_ocr_jobs;
CREATE POLICY p_import_ocr_jobs_tenant_delete
  ON public.import_ocr_jobs
  FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
