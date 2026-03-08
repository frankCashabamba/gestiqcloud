-- Añade porcentaje de depreciación/overhead a recetas
-- Representa el % sobre el costo de materiales destinado a amortizar
-- equipos, maquinaria e infraestructura (valor típico: 5%)
ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS overhead_pct NUMERIC(5, 2) DEFAULT 5;
