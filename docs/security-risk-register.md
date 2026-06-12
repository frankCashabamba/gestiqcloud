# Security Risk Register (vivo)

Registro vivo de riesgos de seguridad de GestiqCloud y su estado. Fuente de detalle:
`GestiqCloud_Auditoria_Base_Tecnica_Consolidada.md`. Actualizar este fichero cuando
cambie el estado de un riesgo.

Leyenda: ✅ cerrado · 🟢 cerrado en dev / PDT prod · 🟡 parcial · 🟠 pendiente · 🔴 abierto crítico

## Núcleo (base técnica)

| ID | Riesgo | Estado | Mitigación / nota |
|---|---|---|---|
| §0.0 | App conectaba como SUPERUSER → RLS bypassed | 🟢 dev / 🟠 prod | Rol `gestiq_app` no-superuser; `verify_rls_isolation.sql` 5/5. PDT: replicar en prod (backend + Celery) |
| 1 | Auth dispersa (múltiples puertas) | ✅ | Puerta única `with_access_claims`; `docs/security/auth-contract.md` |
| 2 | Tenant desde múltiples fuentes / payload | ✅ | `get_tenant_context`; auditoría payload: solo login lo usa (legítimo); RLS cubre escrituras |
| 3 | Sesión DB alternativa sin RLS/GUC | ✅ | `db/session.py` shim de `config/database.py`; `system_session` |
| 4 | Bypass RLS sin inventario | ✅ | `docs/security/bypass-rls-register.md`; solo `system_session`/`bot_session_scope` justificados |
| 5 | CSRF no montado / sin tests | ✅ | `RequireCSRFMiddleware` + `test_csrf_middleware.py`; `docs/security/csrf.md`. PDT: validar tras Worker |
| 6 | Rate limit fragmentado/evadible | ✅ | `EndpointRateLimiter` Redis+fallback; `docs/seguridad.md` |
| 7 | Telemetry duplicada + PII en logs | ✅ | Capa única `telemetry` + `core/redact.py` |
| 8 | Routers legacy/duplicados conviviendo | 🟢 | Montaje único `register_all_routers` + 3 tests invariante; admin migrado a `/api/v1`. PDT: retirar rewrites `/v1` tras 0 tráfico en prod |
| 9 | Workers sin aislamiento multi-tenant | 🟢 dev / 🟠 prod | Workers + importador con `tenant_session_scope`; depende de §0.0 en prod |

## Hallazgos críticos / medios

| ID | Riesgo | Estado | Nota |
|---|---|---|---|
| C-01 | Sesión alternativa sin RLS | ✅ | shim de `config/database.py` |
| C-02 | Workers sin aislamiento | 🟢 | scopes canónicos; RLS real con `gestiq_app` |
| C-03 | Importador carga por id sin tenant | ✅ | filtro `tenant_id` + tests |
| C-04 | Telegram bot con bypass RLS | ✅ | `tenant_session_scope` + `compare_digest` |
| C-05 | CSRF posiblemente no montado | ✅ | montado + tests (ver fila 5) |
| C-06 | Auth/tenant duplicados | ✅ | ver filas 1/2 |
| C-07 | admin_logs sin guard superadmin | ✅ | `require_scope("admin")` |
| M-01 | Webhooks devuelven `str(e)` | ✅ (2026-06-12) | catch-all → detalle genérico + `logger.exception`; dominio (`InvalidWebhookURL`/`WebhookNotFound`) intacto |
| M-02 | Export CSV/XLSX injection | ✅ | `_sanitize_cell` |
| M-03 | Documents upload débil | ✅ | MIME sniff + tamaño + nombre + `created_by=user_id` |
| M-04 | Users escalada (admin/roles desde payload) | ✅ (2026-06-12) | `enforce_user_escalation`: `users:grant_admin` / `users:assign_roles` separados |
| M-05 | Accounting seed sin permiso | ✅ | `PERM_ACCOUNTING_ACCOUNT_MANAGE` |
| M-06 | Routers gruesos (HTTP+SQL+negocio) | 🟠 | Refactor de fondo, baja urgencia |

## Pendientes operativos (no-código)

- 🟠 Desplegar rol `gestiq_app` en producción (VPS): backend **y** Celery (§0.0).
- 🟠 CI: usa `postgres` (superuser) → el invariante de no-superuser hace `skip` (no falla); el aislamiento real lo cubre `verify_rls_isolation.sql`.
- 🟠 Retirar rewrites `/v1` (backend `main.py` + Cloudflare Worker) tras confirmar 0 tráfico `/v1` en prod.
- 🟠 Confirmar en prod que el Worker no elimina `X-CSRF-Token`.
