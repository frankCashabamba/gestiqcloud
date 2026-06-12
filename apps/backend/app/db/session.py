"""SHIM de compatibilidad — la sesión canónica vive en app.config.database.

⚠️ Antes este módulo creaba un `engine` y `SessionLocal` propios **sin** los
GUCs de RLS (`after_begin`), lo que permitía a los workers ejecutar SQL sin el
aislamiento multi-tenant central (hallazgo C-01). Eso ya no ocurre: aquí solo se
re-exporta la única fábrica de sesiones, `app.config.database`.

Para workers/jobs usar los context managers tipados:
  - `tenant_session_scope(tenant_id)` → procesar datos de UN tenant (RLS activo).
  - `system_session()` → barridos de plataforma cross-tenant (bypass_rls).
  - `session_scope()` → uso genérico (tablas sin RLS, p.ej. listar tenants).

Ver docs/security/tenant-context-contract.md y docs/security/bypass-rls-register.md.
"""

from app.config.database import SessionLocal, engine, get_db  # noqa: F401
from app.config.database import session_scope as get_db_context  # noqa: F401

__all__ = ["SessionLocal", "engine", "get_db", "get_db_context"]
