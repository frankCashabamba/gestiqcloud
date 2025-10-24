-- Rollback SPEC-1 tables

DROP TABLE IF EXISTS public.import_log CASCADE;
DROP TABLE IF EXISTS public.production_order CASCADE;
DROP TABLE IF EXISTS public.sale_line CASCADE;
DROP TABLE IF EXISTS public.sale_header CASCADE;
DROP TABLE IF EXISTS public.milk_record CASCADE;
DROP TABLE IF EXISTS public.purchase CASCADE;
DROP TABLE IF EXISTS public.daily_inventory CASCADE;
DROP TABLE IF EXISTS public.uom_conversion CASCADE;
DROP TABLE IF EXISTS public.uom CASCADE;

DROP FUNCTION IF EXISTS public.calculate_daily_inventory_ajuste() CASCADE;
DROP FUNCTION IF EXISTS public.calculate_purchase_total() CASCADE;
