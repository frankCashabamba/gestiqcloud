Migration: Make auth_user global (no tenant_id, no RLS)

Purpose
- Ensure the admin users table `public.auth_user` is not tenant-scoped.
- Remove `tenant_id` column, any RLS policy/index, and disable RLS on this table.

Notes
- Safe to apply repeatedly (guards included).
- Down migration restores the previous tenant-aware state if needed.

