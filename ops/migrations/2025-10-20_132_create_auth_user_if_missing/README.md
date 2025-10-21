Create auth_user if missing (global admin table)

Purpose
- Some environments skipped the baseline, leaving no public.auth_user.
- This migration creates public.auth_user with the expected columns and indexes when missing.

Notes
- No tenant_id column; RLS disabled.

