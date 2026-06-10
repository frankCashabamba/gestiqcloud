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
| RLS-IMP-1 | `modules/importador/tasks.py:~202` (`_run_processing`) | Worker Celery procesa documento sin contexto de request | 1 tenant (parámetro `tenant_id`) | ✅ query filtra `ImpDocumento.id == doc_id AND tenant_id == tenant_id` (2026-06-09) | ❌ pendiente | importador | 2026-06-09 |
| RLS-IMP-2 | `modules/importador/tasks.py:~405` (recuperación payload) | Marcar doc FAILED/unavailable cuando el payload expiró | 1 tenant | ✅ query filtra por `id` + `tenant_id` (2026-06-09) | ❌ pendiente | importador | 2026-06-09 |
| RLS-IMP-3 | `modules/importador/tasks.py:~523` (`analyze_document_ai`) | Análisis IA de un documento ya procesado | 1 tenant | ✅ `analyze_document_with_ai(tenant_id=...)` valida `doc.tenant_id` (2026-06-09) | ❌ pendiente | importador | 2026-06-09 |
| ~~RLS-TG-1~~ | ~~`telegram_bot/.../webhook.py` `_get_bot_db`~~ | **CERRADO (2026-06-10)** | — | ✅ Ya no usa bypass: migrado a `tenant_session_scope(tenant_id)` (GUC, RLS activa). Secret validado con `secrets.compare_digest`. `_get_bot_db` eliminado. | ✅ `test_telegram_webhook.py` | telegram_bot | 2026-06-10 |

## Pendientes (hallazgo C-04 y plan base técnica)

- **RLS-TG-1**: no usar bypass para *leer* datos del tenant; abrir sesión tenant con GUC y reservar bypass solo si es imprescindible. Añadir test con `tenant_id` ajeno y `webhook_secret` inválido.
- Añadir tests cross-tenant a RLS-IMP-1/2/3 (un `doc_id` de tenant B con job de tenant A debe devolver "no encontrado").
- Migrar `app/db/session.py` a wrapper de `app/config/database.py` (C-01) para que ningún worker abra sesiones sin GUC/RLS.

## Regla

```text
Ningún bypass RLS puede existir sin:
- motivo documentado (esta tabla);
- permiso/condición clara;
- test cross-tenant;
- owner técnico;
- fecha de revisión.
```
