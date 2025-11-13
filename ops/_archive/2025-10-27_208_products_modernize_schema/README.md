Modernize products table to the new schema (ORM-aligned).

Summary
- Create table product_categories (if missing).
- Rename legacy columns (nombre -> name, precio_venta -> price).
- Add new columns: stock, unit, product_metadata, category_id.
- Backfill data from legacy columns and map categoria -> product_categories.
- Add indexes on name; keep existing unique(tenant_id, sku).

Notes
- Legacy columns (descripcion, precio_compra, iva_tasa, categoria, activo) are kept for now to avoid breaking unknown code paths. They can be dropped in a follow-up once confirmed unused.

