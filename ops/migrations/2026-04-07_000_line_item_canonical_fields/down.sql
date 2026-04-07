BEGIN;

DELETE FROM imp_field_alias
WHERE canonical_field IN ('description', 'quantity', 'unit_price', 'total_price')
  AND source = 'seed'
  AND tenant_id IS NULL;

DELETE FROM imp_canonical_field
WHERE name IN ('description', 'quantity', 'unit_price', 'total_price');

UPDATE imp_canonical_field SET line_item_slot = NULL, label = NULL WHERE name = 'supplier_ref';

ALTER TABLE imp_canonical_field
    DROP COLUMN IF EXISTS line_item_slot,
    DROP COLUMN IF EXISTS label;

COMMIT;
