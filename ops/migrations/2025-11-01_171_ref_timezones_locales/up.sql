BEGIN;

CREATE TABLE IF NOT EXISTS ref_timezone (
  name TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  offset_minutes INT,
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS ref_locale (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  active BOOLEAN DEFAULT TRUE
);

-- Seeds (minimal)
INSERT INTO ref_timezone(name, display_name, offset_minutes) VALUES
 ('UTC','UTC',0),
 ('Europe/Madrid','Europe/Madrid',60),
 ('America/Guayaquil','America/Guayaquil',-300)
ON CONFLICT (name) DO NOTHING;

INSERT INTO ref_locale(code, name) VALUES
 ('es_ES','Español (España)'),
 ('es_EC','Español (Ecuador)'),
 ('en_US','English (United States)')
ON CONFLICT (code) DO NOTHING;

COMMIT;

