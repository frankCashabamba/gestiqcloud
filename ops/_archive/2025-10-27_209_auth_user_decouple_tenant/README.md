Decouple auth_user from tenant context (no tenant_id).

Summary
- Remove optional coupling introduced by earlier drafts.
- Ensure auth_user remains global; tenant membership handled via usuarios_usuarioempresa.

What it does
- Drops index idx_auth_user_tenant_id if present.
- Drops column auth_user.tenant_id if present.

Rollback
- Restores tenant_id column (NULLable) and recreates the index, if needed.
