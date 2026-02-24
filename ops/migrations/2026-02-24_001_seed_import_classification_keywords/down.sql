-- Rollback: remove seeded classification keywords
DELETE FROM tenant_field_configs WHERE module LIKE 'imports_%';
