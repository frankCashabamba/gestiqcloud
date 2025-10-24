-- Rollback RLS policies for imports module

-- import_ocr_jobs
DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_delete ON public.import_ocr_jobs;
DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_update ON public.import_ocr_jobs;
DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_insert ON public.import_ocr_jobs;
DROP POLICY IF EXISTS p_import_ocr_jobs_tenant_select ON public.import_ocr_jobs;
ALTER TABLE public.import_ocr_jobs DISABLE ROW LEVEL SECURITY;

-- import_attachments
DROP POLICY IF EXISTS p_import_attachments_tenant_delete ON public.import_attachments;
DROP POLICY IF EXISTS p_import_attachments_tenant_update ON public.import_attachments;
DROP POLICY IF EXISTS p_import_attachments_tenant_insert ON public.import_attachments;
DROP POLICY IF EXISTS p_import_attachments_tenant_select ON public.import_attachments;
ALTER TABLE public.import_attachments DISABLE ROW LEVEL SECURITY;

-- import_lineage
DROP POLICY IF EXISTS p_import_lineage_tenant_delete ON public.import_lineage;
DROP POLICY IF EXISTS p_import_lineage_tenant_update ON public.import_lineage;
DROP POLICY IF EXISTS p_import_lineage_tenant_insert ON public.import_lineage;
DROP POLICY IF EXISTS p_import_lineage_tenant_select ON public.import_lineage;
ALTER TABLE public.import_lineage DISABLE ROW LEVEL SECURITY;

-- import_item_corrections
DROP POLICY IF EXISTS p_import_item_corrections_tenant_delete ON public.import_item_corrections;
DROP POLICY IF EXISTS p_import_item_corrections_tenant_update ON public.import_item_corrections;
DROP POLICY IF EXISTS p_import_item_corrections_tenant_insert ON public.import_item_corrections;
DROP POLICY IF EXISTS p_import_item_corrections_tenant_select ON public.import_item_corrections;
ALTER TABLE public.import_item_corrections DISABLE ROW LEVEL SECURITY;

-- import_mappings
DROP POLICY IF EXISTS p_import_mappings_tenant_delete ON public.import_mappings;
DROP POLICY IF EXISTS p_import_mappings_tenant_update ON public.import_mappings;
DROP POLICY IF EXISTS p_import_mappings_tenant_insert ON public.import_mappings;
DROP POLICY IF EXISTS p_import_mappings_tenant_select ON public.import_mappings;
ALTER TABLE public.import_mappings DISABLE ROW LEVEL SECURITY;

-- import_items
DROP POLICY IF EXISTS p_import_items_tenant_delete ON public.import_items;
DROP POLICY IF EXISTS p_import_items_tenant_update ON public.import_items;
DROP POLICY IF EXISTS p_import_items_tenant_insert ON public.import_items;
DROP POLICY IF EXISTS p_import_items_tenant_select ON public.import_items;
ALTER TABLE public.import_items DISABLE ROW LEVEL SECURITY;

-- import_batches
DROP POLICY IF EXISTS p_import_batches_tenant_delete ON public.import_batches;
DROP POLICY IF EXISTS p_import_batches_tenant_update ON public.import_batches;
DROP POLICY IF EXISTS p_import_batches_tenant_insert ON public.import_batches;
DROP POLICY IF EXISTS p_import_batches_tenant_select ON public.import_batches;
ALTER TABLE public.import_batches DISABLE ROW LEVEL SECURITY;
