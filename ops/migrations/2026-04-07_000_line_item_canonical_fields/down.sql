BEGIN;

DELETE FROM imp_field_alias
WHERE canonical_field IN ('description', 'quantity', 'unit_price', 'total_price')
  AND source = 'seed'
  AND tenant_id IS NULL;

DELETE FROM imp_canonical_field
WHERE name IN ('description', 'quantity', 'unit_price', 'total_price');

COMMIT;
