BEGIN;

CREATE TABLE IF NOT EXISTS core_pais (
  id SERIAL PRIMARY KEY,
  codigo CHAR(2) UNIQUE NOT NULL,
  nombre TEXT NOT NULL,
  activo BOOLEAN DEFAULT TRUE
);

-- Semillas mínimas
INSERT INTO core_pais (codigo, nombre) VALUES
  ('ES','España') ON CONFLICT (codigo) DO NOTHING;
INSERT INTO core_pais (codigo, nombre) VALUES
  ('EC','Ecuador') ON CONFLICT (codigo) DO NOTHING;
INSERT INTO core_pais (codigo, nombre) VALUES
  ('US','Estados Unidos') ON CONFLICT (codigo) DO NOTHING;
INSERT INTO core_pais (codigo, nombre) VALUES
  ('MX','México') ON CONFLICT (codigo) DO NOTHING;

COMMIT;
