-- Añadir columna tax_id_type a clients para almacenar el tipo de identificación (CEDULA, RUC, DNI, etc.)
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS tax_id_type VARCHAR(30);
