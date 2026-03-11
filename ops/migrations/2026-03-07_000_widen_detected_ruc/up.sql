-- Widen ruc_detectado from VARCHAR(20) to VARCHAR(100)
-- The LLM sometimes extracts values longer than 20 chars, which causes StringDataRightTruncation.
ALTER TABLE imp_documento
    ALTER COLUMN ruc_detectado TYPE VARCHAR(100),
    ALTER COLUMN llm_model     TYPE VARCHAR(100),
    ALTER COLUMN moneda        TYPE VARCHAR(10);
