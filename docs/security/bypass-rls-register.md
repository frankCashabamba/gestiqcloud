# Registro de bypass RLS

> Inventario vivo de todos los usos de `db.info["bypass_rls"] = True` (o equivalente)
> en el backend. Ningún bypass puede existir sin: motivo documentado, condición/permiso
> claro, test cross-tenant, owner técnico y fecha de revisión.
>
> Última verificación contra código: **2026-06-09**.

## Helpers oficiales (infraestructura, no son hallazgos)

Estos viven en `app/config/database.py` y son la **forma correcta** de activar el bypass de manera acotada y auditada. El resto del código debería usarlos en vez de tocar `db.info` a mano.

| Código | Fichero:línea | Qué hace |
|---|---|---|
| `temp_rls_bypass` | `app/config/database.py:~388` | Context manager que activa `bypass_rls` y lo restaura al salir. |
| `system_session` | `app/config/database.py:~453` | **(2026-06-09)** Sesión de sistema con `bypass_rls=True` (vía `db.info`, reaplicado por `after_begin`) para barridos de plataforma cross-tenant. Usada por `notifications.check_and_notify_low_stock`. El procesamiento por tenant debe ir en `tenant_session_scope`. |
| `bot_session_scope` | `app/config/database.py:~475` | Sesión con `bypass_rls=True` + `app.tenant_id` para webhooks/bots sin sesión de usuario. |

El GUC `app.bypass_rls` también se setea automáticamente para superadmin en `after_begin` (`is_superadmin`).

## Usos en módulos/workers

| Código | Fichero:línea | Motivo | Alcance | Aislamiento real | Test cross-tenant | Owner | Revisión |
|---|---|---|---|---|---|---|---|
| ~~RLS-IMP-1~~ | `importador/tasks.py` `_run_processing` | **CERRADO (2026-06-10)**: bypass eliminado | 1 tenant | ✅ Sin bypass: RLS por `app.tenant_id` (política `tenant_isolation`, solo tenant) + filtro explícito `id AND tenant_id`. Validado con rol no-superuser. | ✅ `test_importador_isolation.py` + suite (361 ok) | importador | 2026-06-10 |
| ~~RLS-IMP-2~~ | `importador/tasks.py` (recuperación payload) | **CERRADO (2026-06-10)**: bypass eliminado | 1 tenant | ✅ Sin bypass: RLS + filtro `id`+`tenant_id`. | ✅ suite importador | importador | 2026-06-10 |
| ~~RLS-IMP-3~~ | `importador/tasks.py` `analyze_document_ai` | **CERRADO (2026-06-10)**: bypass eliminado | 1 tenant | ✅ Sin bypass: RLS + `analyze_document_with_ai` valida `doc.tenant_id`. | ✅ `test_importador_isolation.py` | importador | 2026-06-10 |
| ~~RLS-TG-1~~ | ~~`telegram_bot/.../webhook.py` `_get_bot_db`~~ | **CERRADO (2026-06-10)** | — | ✅ Ya no usa bypass: migrado a `tenant_session_scope(tenant_id)` (GUC, RLS activa). Secret validado con `secrets.compare_digest`. `_get_bot_db` eliminado. | ✅ `test_telegram_webhook.py` | telegram_bot | 2026-06-10 |

## Estado (2026-06-10)

- ✅ RLS-TG-1 (Telegram), RLS-IMP-1/2/3 (importador): **cerrados** — sin bypass, RLS por tenant + filtros explícitos. Bypass restante solo en helpers de plataforma (`system_session`, `bot_session_scope`).
- ✅ `app/db/session.py` convertido en shim de `app/config/database.py` (C-01).
- 🔴 **Bloqueante real**: RLS no protege en la práctica hasta que la app use un rol DB **no-superuser** (ver `docs/security/db-app-role.md`). Con `postgres` (superuser) todo el bypass/aislamiento es irrelevante.

## Regla

```text
Ningún bypass RLS puede existir sin:
- motivo documentado (esta tabla);
- permiso/condición clara;
- test cross-tenant;
- owner técnico;
- fecha de revisión.
```
