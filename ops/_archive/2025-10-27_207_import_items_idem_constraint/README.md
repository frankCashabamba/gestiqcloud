Fix ON CONFLICT for import_items bulk insert by adding a proper unique constraint.

Context:
- Bulk ingest uses INSERT ... ON CONFLICT (batch_id, idempotency_key) DO NOTHING.
- Previous migration created a PARTIAL unique index on (batch_id, idempotency_key)
  with WHERE idempotency_key IS NOT NULL, which PostgreSQL can’t infer
  unless the ON CONFLICT includes the predicate.
- Result: psycopg2.errors.InvalidColumnReference during ingest.

Change:
- Drop the partial unique index if present.
- Add a full UNIQUE constraint on (batch_id, idempotency_key).

Notes:
- UNIQUE in Postgres allows multiple NULLs, so rows with NULL idempotency_key
  continue to be insertable; this preserves intended behavior while allowing
  ON CONFLICT inference to work.

