-- Expande aliases de campos canónicos con variantes faltantes.
-- Agrega campos concept, category, notes que se usaban hardcodeados en router.py.
-- También completa aliases de doc_number con variantes no incluidas en el seed inicial.

-- Completar doc_number con aliases faltantes
INSERT INTO imp_field_alias (tenant_id, canonical_field, alias, priority) VALUES
  (NULL, 'doc_number', 'invoice_no',              4),
  (NULL, 'doc_number', 'factura',                 3),
  (NULL, 'doc_number', 'comprobante',             2)
ON CONFLICT (tenant_id, canonical_field, alias) DO NOTHING;

-- concept: campo de descripción/concepto del documento
INSERT INTO imp_field_alias (tenant_id, canonical_field, alias, priority) VALUES
  (NULL, 'concept', 'concept',         10),
  (NULL, 'concept', 'concepto',        9),
  (NULL, 'concept', 'descripcion',     8),
  (NULL, 'concept', 'description',     7),
  (NULL, 'concept', 'detalle',         6),
  (NULL, 'concept', 'notes',           5),
  (NULL, 'concept', 'nota',            4),
  (NULL, 'concept', 'observaciones',   3),
  (NULL, 'concept', 'productos',       2)
ON CONFLICT (tenant_id, canonical_field, alias) DO NOTHING;

-- category: categoría del documento
INSERT INTO imp_field_alias (tenant_id, canonical_field, alias, priority) VALUES
  (NULL, 'category', 'category',   10),
  (NULL, 'category', 'categoria',  9)
ON CONFLICT (tenant_id, canonical_field, alias) DO NOTHING;
