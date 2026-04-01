BEGIN;

DELETE FROM imp_field_alias WHERE canonical_field = 'supplier_ref' AND source = 'seed';
DELETE FROM imp_canonical_field WHERE name = 'supplier_ref';

COMMIT;
