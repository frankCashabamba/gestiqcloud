-- Reverse: remove the case-insensitive unique index.
-- Note: the deduplicated rows cannot be automatically restored.
DROP INDEX IF EXISTS uq_modules_name_lower;
