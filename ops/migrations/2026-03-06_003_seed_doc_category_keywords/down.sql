DELETE FROM sector_field_defaults
WHERE sector = '_system'
  AND module = 'importador.doc_categories'
  AND field IN ('invoice', 'receipt', 'recipe', 'inventory', 'bank', 'payroll');
