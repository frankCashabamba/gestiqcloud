BEGIN;

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, help, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a201'::uuid,
    '_system',
    'importador.prompt_config',
    'extraction_system',
    TRUE,
    FALSE,
    1,
    'Extraction system prompt',
    'You are a universal accounting document analyzer. Always respond with valid JSON using the configured canonical fields.',
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.prompt_config' AND field = 'extraction_system'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, help, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a202'::uuid,
    '_system',
    'importador.prompt_config',
    'structured_table_note',
    TRUE,
    FALSE,
    2,
    'Structured table note',
    'NOTE: Content is already pre-processed as a structured table. If you recognize a list or table, set is_table=true and provide clean column names. Do NOT return individual rows.',
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.prompt_config' AND field = 'structured_table_note'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, help, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a203'::uuid,
    '_system',
    'importador.prompt_config',
    'doc_type_instruction',
    TRUE,
    FALSE,
    3,
    'Doc type instruction',
    'A short uppercase label describing the document type in English. Use standard business labels when they clearly apply. Use OTHER only if truly unclassifiable.',
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.prompt_config' AND field = 'doc_type_instruction'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, help, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a204'::uuid,
    '_system',
    'importador.prompt_config',
    'critical_rules',
    TRUE,
    FALSE,
    4,
    'Critical extraction rules',
    NULL,
    '[
      "The document may be in any language. Read it as-is and map to the configured canonical fields.",
      "total_amount must represent the grand total, not a quantity.",
      "vendor is the entity that issues or signs the document.",
      "If is_table=true, return columns and only visible summary values in fields.",
      "Extract payment_method and payment_terms when visible.",
      "Dates must use YYYY-MM-DD. Amounts must use dot decimal notation. Missing fields must be null.",
      "Do not invent data absent from the document."
    ]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.prompt_config' AND field = 'critical_rules'
);

COMMIT;
