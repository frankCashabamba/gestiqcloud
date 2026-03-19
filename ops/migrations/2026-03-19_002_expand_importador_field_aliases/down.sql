DELETE FROM imp_field_alias
WHERE tenant_id IS NULL
  AND canonical_field IN ('concept', 'category')
  AND alias IN (
    'concept','concepto','descripcion','description','detalle','notes','nota','observaciones','productos',
    'category','categoria'
  );

DELETE FROM imp_field_alias
WHERE tenant_id IS NULL AND canonical_field = 'doc_number'
  AND alias IN ('invoice_no', 'factura', 'comprobante');
