Fix: Restore auto-increment defaults on all int PK id columns (public schema)

Purpose
- Some environments skipped the baseline or lost DEFAULT/IDENTITY on integer PK id columns.
- This migration scans public.* tables and ensures id (integer/bigint PK) has a default (IDENTITY/sequence).

Notes
- Idempotent and conservative: only affects public tables where PK column name is exactly 'id', type integer/bigint, and has neither IDENTITY nor DEFAULT.
- For each affected table, creates a sequence `<table>_id_seq` (if missing), sets DEFAULT nextval, and advances the sequence to max(id)+1.

