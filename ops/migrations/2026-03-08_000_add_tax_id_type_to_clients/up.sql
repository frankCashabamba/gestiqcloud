-- Add tax_id_type to clients to store the identification type (CEDULA, RUC, DNI, etc.)
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS tax_id_type VARCHAR(30);
