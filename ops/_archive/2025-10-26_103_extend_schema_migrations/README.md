Title: Extend schema_migrations to support admin UI

Summary
- Adds the columns expected by apps/backend/app/routers/migrations.py
- Columns added with IF NOT EXISTS and safe defaults

Columns
- name TEXT
- status TEXT DEFAULT 'pending'
- mode TEXT
- started_at TIMESTAMPTZ
- completed_at TIMESTAMPTZ
- executed_by TEXT
- execution_time_ms INTEGER
- error_message TEXT
- applied_order INTEGER
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()

Post-apply
- Existing rows (if any) will have status NULL; we coerce NULL→'success' when applied_at is present.

