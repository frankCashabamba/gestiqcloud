BEGIN;

CREATE TABLE IF NOT EXISTS core_tipoempresa (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core_tiponegocio (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO core_tipoempresa (id, name, description) VALUES
    (1, 'Retail', 'Retail business'),
    (2, 'Services', 'Professional services'),
    (3, 'Manufacturing', 'Manufacturing & production'),
    (4, 'Food Service', 'Food services')
ON CONFLICT (id) DO NOTHING;

INSERT INTO core_tiponegocio (id, name, description) VALUES
    (1, 'Bakery', 'Bakery'),
    (2, 'General Store', 'General store / Bazaar'),
    (3, 'Auto Repair', 'Auto repair shop'),
    (4, 'Restaurant', 'Restaurant'),
    (5, 'Cafe', 'Café')
ON CONFLICT (id) DO NOTHING;

COMMIT;
