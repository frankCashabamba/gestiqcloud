-- Revert column widths (may fail if data exceeds original limits)
ALTER TABLE imp_documento
    ALTER COLUMN ruc_detectado TYPE VARCHAR(20),
    ALTER COLUMN llm_model     TYPE VARCHAR(50),
    ALTER COLUMN moneda        TYPE VARCHAR(5);
