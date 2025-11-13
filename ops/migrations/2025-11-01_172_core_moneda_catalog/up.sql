BEGIN;

CREATE TABLE IF NOT EXISTS core_moneda (
  id SERIAL PRIMARY KEY,
  codigo VARCHAR(10) UNIQUE NOT NULL,
  nombre TEXT NOT NULL,
  simbolo VARCHAR(5) NOT NULL,
  activo BOOLEAN DEFAULT TRUE
);

-- Semillas mínimas
INSERT INTO core_moneda (codigo, nombre, simbolo) VALUES ('EUR','Euro','€')
ON CONFLICT (codigo) DO NOTHING;
INSERT INTO core_moneda (codigo, nombre, simbolo) VALUES ('USD','US Dollar','$')
ON CONFLICT (codigo) DO NOTHING;

COMMIT;

