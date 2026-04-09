BEGIN;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('filename_normalization', 'uuid_patterns', $$["[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"]$$::jsonb, 'Filename UUID patterns'),
    ('filename_normalization', 'date_patterns', $$["\\b\\d{4}[-_]\\d{2}[-_]\\d{2}\\b","\\b\\d{2}[-_]\\d{2}[-_]\\d{4}\\b"]$$::jsonb, 'Filename date patterns'),
    ('filename_normalization', 'long_number_patterns', $$["\\b\\d{4,}\\b"]$$::jsonb, 'Filename long number patterns'),
    ('filename_normalization', 'separator_patterns', $$["[_\\-\\.]+"]$$::jsonb, 'Filename separator patterns')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, value_text, label) VALUES
    ('tax_id_patterns', 'match_patterns', $$["(?:R\\.?U\\.?C\\.?|RUC|NIF|CIF|CUIT|CUIL|RFC)\\s*[:\\-#]?\\s*([0-9][\\d\\-]{6,19})","\\b(20\\d{9}|10\\d{9})\\b"]$$::jsonb, NULL, 'Tax ID match patterns'),
    ('tax_id_patterns', 'scan_max_chars', NULL, $$3000$$, 'Tax ID scan max chars'),
    ('tax_id_patterns', 'min_digits', NULL, $$8$$, 'Tax ID minimum digits'),
    ('tax_id_patterns', 'max_digits', NULL, $$15$$, 'Tax ID maximum digits')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('routing_field_aliases', 'vendor', $$["vendor","supplier","proveedor","emisor","supplier_name"]$$::jsonb, 'Routing field aliases for vendor'),
    ('routing_field_aliases', 'vendor_tax_id', $$["vendor_tax_id","supplier_tax_id","ruc","tax_id","nif","vat"]$$::jsonb, 'Routing field aliases for vendor_tax_id'),
    ('routing_field_aliases', 'issue_date', $$["issue_date","invoice_date","fecha","date","expense_date"]$$::jsonb, 'Routing field aliases for issue_date'),
    ('routing_field_aliases', 'due_date', $$["due_date","fecha_vencimiento","payment_due_date"]$$::jsonb, 'Routing field aliases for due_date'),
    ('routing_field_aliases', 'doc_number', $$["doc_number","invoice_number","numero_factura","reference","folio"]$$::jsonb, 'Routing field aliases for doc_number'),
    ('routing_field_aliases', 'subtotal', $$["subtotal","base_amount","amount_untaxed","net_amount"]$$::jsonb, 'Routing field aliases for subtotal'),
    ('routing_field_aliases', 'tax_amount', $$["tax_amount","tax","iva","vat_amount","impuesto"]$$::jsonb, 'Routing field aliases for tax_amount'),
    ('routing_field_aliases', 'total_amount', $$["total_amount","monto_total","total","grand_total","importe"]$$::jsonb, 'Routing field aliases for total_amount'),
    ('routing_field_aliases', 'currency', $$["currency","moneda","divisa"]$$::jsonb, 'Routing field aliases for currency'),
    ('routing_field_aliases', 'payment_method', $$["payment_method","forma_pago","metodo_pago","payment_type"]$$::jsonb, 'Routing field aliases for payment_method'),
    ('routing_field_aliases', 'concept', $$["concept","description","concepto","detalle","glosa"]$$::jsonb, 'Routing field aliases for concept'),
    ('routing_field_aliases', 'line_items', $$["line_items","lineas","items"]$$::jsonb, 'Routing field aliases for line_items'),
    ('routing_field_aliases', 'rows', $$["filas","filas_por_hoja"]$$::jsonb, 'Routing field aliases for rows')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('routing_field_labels', 'vendor', $$proveedor$$, 'Routing label for vendor'),
    ('routing_field_labels', 'vendor_tax_id', $$identificacion fiscal$$, 'Routing label for vendor_tax_id'),
    ('routing_field_labels', 'issue_date', $$fecha$$, 'Routing label for issue_date'),
    ('routing_field_labels', 'due_date', $$vencimiento$$, 'Routing label for due_date'),
    ('routing_field_labels', 'doc_number', $$numero$$, 'Routing label for doc_number'),
    ('routing_field_labels', 'subtotal', $$subtotal$$, 'Routing label for subtotal'),
    ('routing_field_labels', 'tax_amount', $$impuesto$$, 'Routing label for tax_amount'),
    ('routing_field_labels', 'total_amount', $$total$$, 'Routing label for total_amount'),
    ('routing_field_labels', 'currency', $$moneda$$, 'Routing label for currency'),
    ('routing_field_labels', 'payment_method', $$forma de pago$$, 'Routing label for payment_method'),
    ('routing_field_labels', 'concept', $$concepto$$, 'Routing label for concept'),
    ('routing_field_labels', 'line_items', $$lineas$$, 'Routing label for line_items'),
    ('routing_field_labels', 'rows', $$filas$$, 'Routing label for rows')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('routing_fallback_profiles', 'supplier_invoice', $${
  "code": "supplier_invoice",
  "document_type": "supplier_invoice",
  "suggested_destination": "supplier_invoice",
  "required_groups": [["issue_date"], ["total_amount"]],
  "support_fields": ["vendor", "vendor_tax_id", "subtotal", "tax_amount", "doc_number", "currency", "line_items"],
  "explanation_fields": ["vendor", "issue_date", "subtotal", "tax_amount", "total_amount"],
  "blocked": false,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile supplier_invoice'),
    ('routing_fallback_profiles', 'expense', $${
  "code": "expense",
  "document_type": "expense",
  "suggested_destination": "expense",
  "required_groups": [["issue_date"], ["total_amount"], ["concept", "vendor", "doc_number"]],
  "support_fields": ["tax_amount", "currency", "payment_method"],
  "explanation_fields": ["concept", "vendor", "issue_date", "tax_amount", "total_amount"],
  "blocked": false,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile expense'),
    ('routing_fallback_profiles', 'recipe', $${
  "code": "recipe",
  "document_type": "recipe",
  "suggested_destination": "recipe",
  "required_groups": [["rows", "line_items"]],
  "support_fields": ["doc_number"],
  "explanation_fields": ["rows", "line_items"],
  "blocked": false,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile recipe'),
    ('routing_fallback_profiles', 'inventory', $${
  "code": "inventory",
  "document_type": "inventory",
  "required_groups": [["rows", "line_items"]],
  "support_fields": ["doc_number"],
  "explanation_fields": ["rows", "line_items"],
  "blocked": true,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile inventory'),
    ('routing_fallback_profiles', 'bank_statement', $${
  "code": "bank_statement",
  "document_type": "bank_statement",
  "required_groups": [["issue_date"], ["rows", "line_items"]],
  "support_fields": ["currency"],
  "explanation_fields": ["issue_date", "rows"],
  "blocked": true,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile bank_statement'),
    ('routing_fallback_profiles', 'payroll', $${
  "code": "payroll",
  "document_type": "payroll",
  "required_groups": [["issue_date"], ["rows", "line_items"]],
  "support_fields": ["total_amount"],
  "explanation_fields": ["issue_date", "rows", "total_amount"],
  "blocked": true,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile payroll'),
    ('routing_fallback_profiles', 'other', $${
  "code": "other",
  "document_type": "expense",
  "suggested_destination": "expense",
  "required_groups": [["issue_date"], ["total_amount"]],
  "support_fields": ["concept", "vendor", "tax_amount"],
  "explanation_fields": ["concept", "vendor", "issue_date", "total_amount"],
  "blocked": false,
  "confidence_threshold": 0.8
}$$, 'Routing fallback profile other')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('routing_fallback_rules', 'category.invoice', $$["source_kind=category","source_key=invoice","profile_code=supplier_invoice","priority=100"]$$::jsonb, 'Routing fallback rule category.invoice'),
    ('routing_fallback_rules', 'category.receipt', $$["source_kind=category","source_key=receipt","profile_code=expense","priority=100"]$$::jsonb, 'Routing fallback rule category.receipt'),
    ('routing_fallback_rules', 'category.recipe', $$["source_kind=category","source_key=recipe","profile_code=recipe","priority=100"]$$::jsonb, 'Routing fallback rule category.recipe'),
    ('routing_fallback_rules', 'category.inventory', $$["source_kind=category","source_key=inventory","profile_code=inventory","priority=100"]$$::jsonb, 'Routing fallback rule category.inventory'),
    ('routing_fallback_rules', 'category.bank', $$["source_kind=category","source_key=bank","profile_code=bank_statement","priority=100"]$$::jsonb, 'Routing fallback rule category.bank'),
    ('routing_fallback_rules', 'category.payroll', $$["source_kind=category","source_key=payroll","profile_code=payroll","priority=100"]$$::jsonb, 'Routing fallback rule category.payroll'),
    ('routing_fallback_rules', 'category.other', $$["source_kind=category","source_key=other","profile_code=other","priority=100"]$$::jsonb, 'Routing fallback rule category.other'),
    ('routing_fallback_rules', 'doc_type.other', $$["source_kind=doc_type","source_key=OTHER","profile_code=other","priority=100"]$$::jsonb, 'Routing fallback rule doc_type.other')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('amount_label_config', 'total_amount', $$["valor total","importe total","total a pagar","grand total","amount due","payable amount","monto total","total"]$$::jsonb, 'Amount labels for total_amount'),
    ('amount_label_config', 'subtotal', $$["subtotal sin impuestos","total sin impuestos","tax exclusive amount","base imponible","sub total","subtotal"]$$::jsonb, 'Amount labels for subtotal'),
    ('amount_label_config', 'tax_amount', $$["iva","vat","igv","gst","tax amount","impuesto"]$$::jsonb, 'Amount labels for tax_amount')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('pdf_table_parse', 'unit_values', $$["ml","mg","g","kg","l","lt","lts","unit","unid","unidad","unidades","oz","pz","pza","m","cm","mm","lb","gr"]$$::jsonb, 'PDF table unit values'),
    ('pdf_table_parse', 'footer_skip_patterns', $$["pagina\\s+\\d","page\\s+\\d","pag\\.?\\s+\\d","pagina\\s+de\\s+\\d"]$$::jsonb, 'PDF table footer skip patterns')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, value_list, label) VALUES
    ('ai_params', 'temperature', $$0.1$$, NULL, 'AI temperature'),
    ('ai_params', 'max_tokens_extraction', $$1500$$, NULL, 'AI max tokens extraction'),
    ('ai_params', 'max_tokens_classification', $$220$$, NULL, 'AI max tokens classification'),
    ('ai_params', 'content_limit_unstructured', $$7000$$, NULL, 'AI content limit unstructured'),
    ('ai_params', 'content_limit_structured', $$4000$$, NULL, 'AI content limit structured'),
    ('ai_params', 'max_tokens_by_doctype', NULL, $$["INVOICE=1200","RECEIPT=600","PAYROLL=800","BANK_STATEMENT=500","INVENTORY=400","COSTING=600","OTHER=1500"]$$::jsonb, 'AI max tokens by document type')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, value_list, label) VALUES
    ('ai_runtime', 'ocr_min_quality', $$0.45$$, NULL, 'OCR minimum quality'),
    ('ai_runtime', 'ocr_min_words_for_vision', $$18$$, NULL, 'OCR minimum words for vision'),
    ('ai_runtime', 'ocr_length_target_chars', $$1200$$, NULL, 'OCR length target chars'),
    ('ai_runtime', 'ocr_word_target', $$180$$, NULL, 'OCR word target'),
    ('ai_runtime', 'ocr_alpha_ratio_target', $$0.60$$, NULL, 'OCR alpha ratio target'),
    ('ai_runtime', 'ocr_noise_ratio_limit', $$0.20$$, NULL, 'OCR noise ratio limit'),
    ('ai_runtime', 'ocr_score_weight_length', $$0.35$$, NULL, 'OCR score weight length'),
    ('ai_runtime', 'ocr_score_weight_words', $$0.35$$, NULL, 'OCR score weight words'),
    ('ai_runtime', 'ocr_score_weight_alpha', $$0.20$$, NULL, 'OCR score weight alpha'),
    ('ai_runtime', 'ocr_score_weight_clean', $$0.10$$, NULL, 'OCR score weight clean'),
    ('ai_runtime', 'ocr_guard_confidence_cap', $$0.45$$, NULL, 'OCR guard confidence cap'),
    ('ai_runtime', 'ocr_evidence_formats', NULL, $$["IMAGE_OCR","PDF_OCR","PDF","JPG","JPEG","PNG","IMG","HEIC","WEBP"]$$::jsonb, 'OCR evidence formats'),
    ('ai_runtime', 'vision_allowed_formats', NULL, $$["IMAGE_OCR","PDF_OCR","JPG","PNG","IMG","PDF"]$$::jsonb, 'Vision allowed formats'),
    ('ai_runtime', 'evidence_stop_tokens', NULL, $$["cliente","customer","proveedor","vendor","empresa","company","concepto","concept"]$$::jsonb, 'Evidence stop tokens'),
    ('ai_runtime', 'currency_markers', $${
  "USD": ["usd", "us$", "$", "dolar", "dolares"],
  "EUR": ["eur", "euro", "euros", "€"],
  "PEN": ["pen", "s/", "sol", "soles"],
  "$": ["$", "usd", "dolar", "dolares"],
  "S/": ["s/", "pen", "sol", "soles"]
}$$, NULL, 'Currency markers'),
    ('ai_runtime', 'ocr_written_months', $${
  "enero": "1",
  "febrero": "2",
  "marzo": "3",
  "abril": "4",
  "mayo": "5",
  "junio": "6",
  "julio": "7",
  "agosto": "8",
  "septiembre": "9",
  "setiembre": "9",
  "octubre": "10",
  "noviembre": "11",
  "diciembre": "12"
}$$, NULL, 'OCR written months'),
    ('ai_runtime', 'low_evidence_reason_template', $$Low OCR evidence: cleared {cleared} unsupported field(s) to avoid hallucinated data.$$, NULL, 'Low evidence reason template'),
    ('ai_runtime', 'vision_default_reasoning', $$Vision model analysis$$, NULL, 'Vision default reasoning'),
    ('ai_runtime', 'vision_resize_max_dim', $$1024$$, NULL, 'Vision resize max dim'),
    ('ai_runtime', 'vision_temperature', $$0.10$$, NULL, 'Vision temperature'),
    ('ai_runtime', 'vision_num_predict', $$600$$, NULL, 'Vision num predict'),
    ('ai_runtime', 'vision_probe_timeout_seconds', $$5$$, NULL, 'Vision probe timeout seconds'),
    ('ai_runtime', 'vision_timeout_seconds', $$45$$, NULL, 'Vision timeout seconds'),
    ('ai_runtime', 'openai_fallback_enabled', $$true$$, NULL, 'OpenAI fallback enabled'),
    ('ai_runtime', 'openai_fallback_on_error', $$false$$, NULL, 'OpenAI fallback on error'),
    ('ai_runtime', 'openai_fallback_on_slow', $$true$$, NULL, 'OpenAI fallback on slow'),
    ('ai_runtime', 'openai_fallback_on_complex', $$true$$, NULL, 'OpenAI fallback on complex'),
    ('ai_runtime', 'openai_fallback_complexity_threshold', $$0.72$$, NULL, 'OpenAI fallback complexity threshold'),
    ('ai_runtime', 'openai_fallback_slow_threshold_ms', $$15000$$, NULL, 'OpenAI fallback slow threshold ms'),
    ('ai_runtime', 'openai_fallback_prompt_chars_threshold', $$7000$$, NULL, 'OpenAI fallback prompt chars threshold'),
    ('ai_runtime', 'openai_fallback_content_chars_threshold', $$7000$$, NULL, 'OpenAI fallback content chars threshold'),
    ('ai_runtime', 'openai_fallback_word_count_threshold', $$120$$, NULL, 'OpenAI fallback word count threshold'),
    ('ai_runtime', 'openai_fallback_line_count_threshold', $$30$$, NULL, 'OpenAI fallback line count threshold'),
    ('ai_runtime', 'openai_fallback_ocr_quality_threshold', $$0.45$$, NULL, 'OpenAI fallback OCR quality threshold')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('ai_model_routing', 'default', $$$$, 'AI routing default model'),
    ('ai_model_routing', 'INVOICE', $$$$, 'AI routing model for INVOICE'),
    ('ai_model_routing', 'RECEIPT', $$$$, 'AI routing model for RECEIPT'),
    ('ai_model_routing', 'PAYROLL', $$$$, 'AI routing model for PAYROLL'),
    ('ai_model_routing', 'BANK_STATEMENT', $$$$, 'AI routing model for BANK_STATEMENT'),
    ('ai_model_routing', 'INVENTORY', $$$$, 'AI routing model for INVENTORY'),
    ('ai_model_routing', 'COSTING', $$$$, 'AI routing model for COSTING'),
    ('ai_model_routing', 'EXPENSE', $$$$, 'AI routing model for EXPENSE')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('learning_control', 'rerun_enabled', $$true$$, 'Learning rerun enabled'),
    ('learning_control', 'rerun_min_confidence', $$0.0$$, 'Learning rerun minimum confidence'),
    ('learning_control', 'rerun_max_snapshot_age_days', $$0$$, 'Learning rerun max snapshot age days'),
    ('learning_control', 'rerun_require_missing_fields', $$false$$, 'Learning rerun requires missing fields'),
    ('learning_control', 'skip_reprocess_confirmed', $$false$$, 'Learning skip reprocess confirmed')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('cache_ttls', 'ocr_ttl_seconds', $$300$$, 'OCR cache TTL seconds'),
    ('cache_ttls', 'pre_classifier_ttl_seconds', $$300$$, 'Pre-classifier cache TTL seconds'),
    ('cache_ttls', 'runtime_config_ttl_seconds', $$300$$, 'Runtime config cache TTL seconds')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, value_list, label) VALUES
    ('processing_runtime', 'ocr_text_sufficient_min_chars', $$100$$, NULL, 'OCR text sufficient minimum chars'),
    ('processing_runtime', 'llm_text_preview_chars', $$6000$$, NULL, 'LLM text preview chars'),
    ('processing_runtime', 'structured_preview_rows', $$5$$, NULL, 'Structured preview rows'),
    ('processing_runtime', 'structured_preview_fields', $$8$$, NULL, 'Structured preview fields'),
    ('processing_runtime', 'doc_type_hint_min_confidence', $$0.65$$, NULL, 'Doc type hint minimum confidence'),
    ('processing_runtime', 'structured_output_rows_limit', $$200$$, NULL, 'Structured output rows limit'),
    ('processing_runtime', 'persist_text_ocr_max_chars', $$50000$$, NULL, 'Persist OCR text max chars'),
    ('processing_runtime', 'ai_failure_tokens', NULL, $$["timeout","timed out","unavailable","connection","refused","failed"]$$::jsonb, 'AI failure tokens'),
    ('processing_runtime', 'table_only_doc_types', NULL, $$["INVENTORY","PRICE_LIST","COSTING","PAYROLL","BANK_STATEMENT","BANK_MOVEMENTS","PRODUCT_LIST"]$$::jsonb, 'Table only doc types'),
    ('processing_runtime', 'product_like_doc_types', NULL, $$["INVENTORY","PRICE_LIST","PRODUCT_LIST","PRODUCTS"]$$::jsonb, 'Product-like doc types'),
    ('processing_runtime', 'recipe_name_field_candidates', NULL, $$["nombre_de_la_receta","nombre_receta","nombre de la receta","nombre"]$$::jsonb, 'Recipe name field candidates')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('reprocess_control', 'enable_premium_deep_reprocess', $$false$$, 'Enable premium deep reprocess'),
    ('reprocess_control', 'deep_premium_provider', $$openai$$, 'Deep premium provider'),
    ('reprocess_control', 'deep_reprocess_prompt_suffix', $$Deep reprocess: re-read the document from scratch, ignore prior OCR/AI results, and prioritize any required fields that were previously missing.$$,
     'Deep reprocess prompt suffix')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('routing_scoring', 'ai_confidence_weight', $$0.60$$, 'Routing scoring AI confidence weight'),
    ('routing_scoring', 'required_ratio_weight', $$0.25$$, 'Routing scoring required ratio weight'),
    ('routing_scoring', 'support_ratio_weight', $$0.10$$, 'Routing scoring support ratio weight'),
    ('routing_scoring', 'category_bonus_weight', $$0.05$$, 'Routing scoring category bonus weight'),
    ('routing_scoring', 'other_category_bonus', $$0.72$$, 'Routing scoring other category bonus'),
    ('routing_scoring', 'blocked_confidence_cap', $$0.58$$, 'Routing scoring blocked confidence cap')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('fuzzy_reuse', 'excel_min_overlap', $$0.80$$, 'Fuzzy reuse minimum Excel overlap'),
    ('fuzzy_reuse', 'learning_min_confidence', $$0.6$$, 'Fuzzy reuse minimum learning confidence')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('snapshot_learning', 'max_examples', $$5$$, 'Snapshot learning max examples'),
    ('snapshot_learning', 'min_stem_len', $$3$$, 'Snapshot learning min stem length'),
    ('snapshot_learning', 'max_stem_len', $$35$$, 'Snapshot learning max stem length'),
    ('snapshot_learning', 'min_alias_len', $$2$$, 'Snapshot learning min alias length'),
    ('snapshot_learning', 'max_alias_len', $$50$$, 'Snapshot learning max alias length')
ON CONFLICT (module, key) DO NOTHING;

COMMIT;
