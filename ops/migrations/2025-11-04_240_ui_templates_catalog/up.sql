-- UI Templates catalog
CREATE TABLE IF NOT EXISTS ui_templates (
  id SERIAL PRIMARY KEY,
  slug VARCHAR(100) UNIQUE NOT NULL,
  label VARCHAR(150) NOT NULL,
  description TEXT,
  pro BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  ord INT,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Seed common templates
INSERT INTO ui_templates (slug, label, description, pro, ord) VALUES
  ('default', 'Default', 'Plantilla base', FALSE, 10),
  ('retail', 'Retail', 'Comercio minorista / bazar', FALSE, 20),
  ('retail_pro', 'Retail Pro', 'Versión avanzada Retail', TRUE, 21),
  ('panaderia', 'Panadería', 'Panadería / obrador', FALSE, 30),
  ('panaderia_pro', 'Panadería Pro', 'Versión avanzada Panadería', TRUE, 31),
  ('taller', 'Taller', 'Servicios, mecánica, reparaciones', FALSE, 40),
  ('taller_pro', 'Taller Pro', 'Versión avanzada Taller', TRUE, 41),
  ('todoa100', 'Todo a 100 (Retail)', 'Alias de Retail', FALSE, 22)
ON CONFLICT (slug) DO NOTHING;
