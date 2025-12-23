BEGIN;

-- Remove seeded countries/locales/timezones by code/name
DELETE FROM countries WHERE code IN ('EC','ES','US','MX','PE','CO','AR','CL','BR','FR');
DELETE FROM locales WHERE code IN ('es_ES','es_EC','es_MX','es_PE','en_US');
DELETE FROM timezones WHERE name IN (
  'Europe/Madrid',
  'America/Guayaquil',
  'America/Mexico_City',
  'America/Lima',
  'America/Bogota',
  'America/Argentina/Buenos_Aires',
  'America/Santiago',
  'America/Sao_Paulo',
  'America/New_York',
  'UTC'
);

COMMIT;
