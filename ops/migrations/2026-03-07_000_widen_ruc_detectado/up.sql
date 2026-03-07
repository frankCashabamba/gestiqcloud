-- Ampliar ruc_detectado de VARCHAR(20) a VARCHAR(100)
-- El LLM a veces extrae valores más largos que 20 chars causando StringDataRightTruncation.
ALTER TABLE imp_documento
    ALTER COLUMN ruc_detectado TYPE VARCHAR(100),
    ALTER COLUMN llm_model     TYPE VARCHAR(100),
    ALTER COLUMN moneda        TYPE VARCHAR(10);
