BEGIN;

-- Seed countries (ISO 3166-1 alpha-2)
INSERT INTO countries (code, name, active) VALUES
  ('EC', 'Ecuador', true),
  ('ES', 'España', true),
  ('US', 'Estados Unidos', true),
  ('MX', 'México', true),
  ('PE', 'Perú', true),
  ('CO', 'Colombia', true),
  ('AR', 'Argentina', true),
  ('CL', 'Chile', true),
  ('BR', 'Brasil', true),
  ('FR', 'Francia', true)
ON CONFLICT (code) DO NOTHING;

-- Seed locales
INSERT INTO locales (code, name, active) VALUES
  ('es_ES', 'Español (España)', true),
  ('es_EC', 'Español (Ecuador)', true),
  ('es_MX', 'Español (México)', true),
  ('es_PE', 'Español (Perú)', true),
  ('en_US', 'English (United States)', true)
ON CONFLICT (code) DO NOTHING;

-- Seed timezones (name is PK)
INSERT INTO timezones (name, display_name, offset_minutes, active) VALUES
  ('Europe/Madrid', 'Europe/Madrid (UTC+1/+2)', 60, true),
  ('America/Guayaquil', 'America/Guayaquil (UTC-5)', -300, true),
  ('America/Mexico_City', 'America/Mexico_City (UTC-6/-5)', -360, true),
  ('America/Lima', 'America/Lima (UTC-5)', -300, true),
  ('America/Bogota', 'America/Bogota (UTC-5)', -300, true),
  ('America/Argentina/Buenos_Aires', 'America/Argentina/Buenos_Aires (UTC-3)', -180, true),
  ('America/Santiago', 'America/Santiago (UTC-4/-3)', -240, true),
  ('America/Sao_Paulo', 'America/Sao_Paulo (UTC-3)', -180, true),
  ('America/New_York', 'America/New_York (UTC-5/-4)', -300, true),
  ('UTC', 'Coordinated Universal Time', 0, true)
ON CONFLICT (name) DO NOTHING;

COMMIT;
