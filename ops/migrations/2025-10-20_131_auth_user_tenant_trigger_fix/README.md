Fix: Detach tenant auto-fill trigger from auth_user (admin table)

Purpose
- Ensure admin table `public.auth_user` has no tenant_id trigger attached.
- Prevent errors like: "record NEW has no field tenant_id" when inserting SuperUser.

Notes
- Idempotent: dynamically drops any trigger on `auth_user` that calls function `set_tenant_id`.

