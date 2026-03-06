-- Seed doc_type classification keywords into sector_field_defaults.
-- sector='_system', module='importador.doc_categories'
-- field = internal category name, options = array of keyword substrings to match against doc_type.
-- These replace all hardcoded keyword lists in the backend/frontend code.
-- To add new types or languages: INSERT or UPDATE these rows in DB — zero code changes needed.

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, options) VALUES
  (gen_random_uuid(), '_system', 'importador.doc_categories', 'invoice', true, false,
   '["INVOICE","FACTURA","RECHNUNG","FATTURA","FATURA","FACTURE","CREDIT_NOTE","NOTA_CREDITO",
     "PURCHASE_ORDER","ORDEN_COMPRA","QUOTE","PRESUPUESTO","PROFORMA","DELIVERY_NOTE",
     "DEVIS","BON_DE_COMMANDE","LIEFERSCHEIN","FATTURA_ELETTRONICA","NOTA_FISCAL"]'::jsonb),

  (gen_random_uuid(), '_system', 'importador.doc_categories', 'receipt', true, false,
   '["RECEIPT","TICKET","VOUCHER","RECIBO","BOLETA","TICKETDEVENTA",
     "REÇU","QUITTUNG","SCONTRINO","NOTA_VENTA","NOTA_DE_VENTA"]'::jsonb),

  (gen_random_uuid(), '_system', 'importador.doc_categories', 'recipe', true, false,
   '["COSTING","COSTEO","RECIPE","RECETA","KALKULATION","CALCUL_COUT",
     "FOOD_COST","COSTO_PRODUCCION","FICHA_TECNICA"]'::jsonb),

  (gen_random_uuid(), '_system', 'importador.doc_categories', 'inventory', true, false,
   '["INVENTORY","INVENTARIO","INVENTAR","PRICE_LIST","LISTA_PRECIOS",
     "PREISLISTE","CATALOGUE","CATALOGO","STOCK","BESTANDSLISTE","LISTINO"]'::jsonb),

  (gen_random_uuid(), '_system', 'importador.doc_categories', 'bank', true, false,
   '["BANK_STATEMENT","EXTRACTO_BANCARIO","KONTOAUSZUG","BANK_MOVEMENTS",
     "MOVIMIENTOS_BANCARIOS","ESTADO_CUENTA","RELEVÉ","EXTRAIT_COMPTE",
     "ESTRATTO_CONTO","ACCOUNT_STATEMENT"]'::jsonb),

  (gen_random_uuid(), '_system', 'importador.doc_categories', 'payroll', true, false,
   '["PAYROLL","NOMINA","PLANILLA","LOHNABRECHNUNG","BULLETIN_PAIE",
     "ROL_PAGOS","SALARY","BUSTA_PAGA","LIQUIDACION"]'::jsonb)

ON CONFLICT DO NOTHING;
