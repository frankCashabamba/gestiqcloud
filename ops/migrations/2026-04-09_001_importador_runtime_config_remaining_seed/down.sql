BEGIN;

DELETE FROM imp_config
WHERE module IN (
    'filename_normalization',
    'tax_id_patterns',
    'routing_field_aliases',
    'routing_field_labels',
    'routing_fallback_profiles',
    'routing_fallback_rules',
    'amount_label_config',
    'pdf_table_parse',
    'ai_params',
    'ai_runtime',
    'ai_model_routing',
    'learning_control',
    'cache_ttls',
    'processing_runtime',
    'reprocess_control',
    'routing_scoring',
    'fuzzy_reuse',
    'snapshot_learning'
);

COMMIT;
