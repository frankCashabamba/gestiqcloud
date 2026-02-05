# Plan de remediacion de debilidades criticas

Este documento consolida las debilidades indicadas y propone acciones
concretas para solucionarlas. Incluye evidencias, riesgos, pasos, y
criterios de salida por tema.

> **Última actualización:** 17 Enero 2026
> **Fecha de cierre del refactor:** 14 Febrero 2026
> **Documento de referencia para refactor:** [docs/REFACTOR_STATUS.md](docs/REFACTOR_STATUS.md)

## Resumen ejecutivo

Estado general: proyecto utilizable pero con riesgo operativo por
refactor en curso, pruebas front-end insuficientes, y debilidades
de despliegue/estandarizacion. El objetivo es estabilizar el sistema
y reducir riesgos de regresion y de despliegue manual.

### Progreso de remediación

| Área | Estado | Notas |
|------|--------|-------|
| CI/CD | ✅ Completado | Lint + deploy staging automático |
| Testing Admin | ✅ Completado | 8 tests con Vitest |
| Playwright E2E | ✅ Completado | 3 flujos configurados |
| Logging estructurado | ✅ Completado | Reemplazados print/except silenciosos |
| Migración sync_conflict_log | ✅ Completado | ops/migrations/2026-01-17_001_sync_conflict_log |
| ESLint imports | ✅ Completado | Configurado en admin y tenant |
| normalize_models.py | ✅ Completado | Marcado como deprecated |
| Documentación refactor | ✅ Completado | Consolidado en docs/REFACTOR_STATUS.md |
| Testing Tenant | ✅ Completado | 69+ tests agregados |
| Contratos API | ✅ Completado | docs/API_CONTRACTS.md |
| k6 Load Testing | ✅ Completado | ops/k6/ con 3 escenarios |
| Benchmarks ElectricSQL | ✅ Completado | ops/benchmarks/electric/ |
| Inventario DTOs | ✅ Completado | docs/DTO_INVENTORY.md |
| Deploy Producción | ✅ Completado | CI con environment protection |
| Routers legacy | ✅ Completado | 23 routers migrados a patrón modular |
| UI módulos core | ✅ Completado | Solo 2 placeholders pendientes |
| Observabilidad | ✅ Completado | Sentry + Prometheus + OpenTelemetry |
| Internacionalización | ✅ Completado | react-i18next + backend i18n (en/es) |

## Alcance

- Backend (apps/backend)
- Frontend Admin (apps/admin)
- Frontend Tenant (apps/tenant)
- CI/CD (GitHub Actions, Render)
- Documentacion y deuda tecnica

## Metodo de verificacion

Se verificaron archivos locales del repo. Los puntos que no son
verificables con evidencia directa se marcan como "pendiente".
Se corrigieron varias afirmaciones que no coinciden con el repo.

## Debilidades criticas y plan de solucion

Notas:
- "Verificado": evidencia en repo.
- "Pendiente": requiere validacion adicional.

### 1) Refactorizacion incompleta (CRITICO)

Evidencia (verificado):
- README indica "En refactor y re-documentacion" en README.md:5.
- Existen 13 documentos con prefijos ANALISIS_/RESUMEN_/TRACKING_.

Pendiente:
- Commit history con reescritura completa (requiere analisis de historia).
- "30+ modulos nuevos sin UI" no verificado; se detectaron 4 modulos nuevos
  con UI basica en tenant/admin (ver Modulos nuevos).

Riesgo:
- Inestabilidad funcional y deuda tecnica por cambios a medio camino.

Plan de remediacion:
- Congelar estructura de modulos (definir que rutas, contratos y
  modelos quedan como definitivos).
- Consolidar documentacion de refactor en un solo documento vivo.
- Definir fecha de cierre del refactor y criterios de "done".
- Crear matriz backend->frontend (modulos y UI) y cerrar gaps.

Checklist:
- [x] Documento unico de refactor en docs/. → docs/REFACTOR_STATUS.md
- [x] Lista de modulos con estado (UI completa / parcial / sin UI). → Matriz en REFACTOR_STATUS.md
- [x] Contratos API unificados y versionados. → docs/API_CONTRACTS.md
- [x] Fecha de cierre publicada. → 14 Febrero 2026

Criterio de salida:
- Sin documentos ANALISIS_/RESUMEN_/TRACKING_ activos y refactor
  cerrado con aprobacion.
- **Fecha límite: 14 Febrero 2026**

### 2) Testing frontend (CRITICO)

Estado (verificado):
- Hay tests en tenant con Vitest y testing library (apps/tenant).
- No hay Playwright/Cypress en repo.
- No hay E2E automatizado ni coverage minimo definido.

Pendiente:
- "testing por email" (solo existe checklist manual).

Riesgo:
- Cambios de UI rompen flujos criticos sin deteccion temprana.

Plan de remediacion:
- Definir suite minima de tests unitarios y de integracion en tenant.
- Agregar pruebas basicas en admin (al menos smoke + rutas criticas).
- Implementar E2E con Playwright (login, navegacion principal,
  flujos de importacion, ventas).
- Agregar cobertura minima exigida por CI.

Checklist:
- [x] Configurar Playwright y 3 flujos criticos E2E. → playwright.config.ts + e2e/
- [x] Aumentar cobertura de unit tests a >= 30% en tenant. → 69+ tests agregados
- [x] Agregar al menos 5 tests en admin. → apps/admin/src/__tests__/smoke.test.tsx (8 tests)
- [x] CI bloquea merges con tests fallando. → .github/workflows/ci.yml

Criterio de salida:
- Playwright corriendo en CI, cobertura minima aprobada.

### 3) CI/CD ausente (CRITICO)

Estado (verificado):
- Existen workflows en .github/workflows (ci.yml, webapps.yml, etc.).
- Hay pre-commit config en .pre-commit-config.yaml.
- No hay despliegue automatico en workflows.
- No hay Dockerfiles ni pipelines de build Docker.

Riesgo:
- Errores humanos en despliegues y falta de validaciones.

Plan de remediacion:
- Consolidar CI en 1 workflow principal con stages claros.
- Agregar pre-commit al onboarding (documentar y exigir).
- Crear pipeline de deploy a staging y prod (con aprobaciones).
- Versionar artefactos y anexar build metadata.

Checklist:
- [x] CI unico con lint + test + build (BE/FE). → .github/workflows/ci.yml consolidado
- [x] Deploy a staging automatico en merges a main. → job deploy-staging agregado
- [x] Deploy a prod con aprobacion manual. → job deploy-production con environment protection
- [x] Notificaciones de estado en PR. → GitHub Actions status checks nativos

Criterio de salida:
- Deploy automatizado y reproducible, sin pasos manuales criticos.

### 4) Inconsistencia en codigo

Estado (verificado):
- Rutas de API mezcladas (routers/ y modules/*/interface/http/).
- Imports inconsistentes en frontend (@/ y relativos).

Pendiente:
- Duplicacion de schemas/DTOs (requiere mapeo).
- Modulos con UI incompleta (usuario indica 4 nuevos).

Riesgo:
- Deuda tecnica, friccion de desarrollo, bugs por contratos duplicados.

Plan de remediacion:
- Definir patron unico para APIs (modular o router centralizado).
- Definir alias unificado para imports y forzar con lint.
- Auditar y consolidar DTOs duplicados.
- Crear y cerrar matriz de modulos: backend/contract/UI.

Checklist:
- [x] Documento de patron API (1 solo). → API_CENTRALIZATION_PATTERN.md + docs/API_CONTRACTS.md
- [x] ESLint o TS config para forzar alias. → apps/admin/eslint.config.js + apps/tenant/eslint.config.js
- [x] Inventario y consolidacion de DTOs. → docs/DTO_INVENTORY.md
- [x] UI completa para modulos marcados como core. → Solo 2 placeholders (einvoicing, reconciliation), resto completo o no requiere UI

Criterio de salida:
- Codigo consistente y sin duplicidad de contratos.

### 5) Performance & scalability unknowns

Estado (verificado):
- No hay k6/JMeter/Locust.
- ElectricSQL sin benchmarks formales.
- Redis solo para workers; caching API no definido en render.yaml.
- OCR workers sin analisis de throughput.

Riesgo:
- Rendimiento desconocido bajo carga y costos operativos altos.

Plan de remediacion:
- Definir objetivos p95 (latencia, sync y OCR).
- Implementar k6 con escenarios multi-tenant.
- Medir ElectricSQL con datasets grandes (100MB).
- Definir estrategia de cache (Redis) para endpoints criticos.
- Añadir limites y metricas para OCR.

Checklist:
- [x] Suite k6 con 3 escenarios base. → scripts/k6/ con escenarios smoke, load, stress
- [x] Reporte de p95 latency + throughput. → ops/k6/ con thresholds definidos
- [x] Benchmarks ElectricSQL. → ops/benchmarks/electric/ + docs/ELECTRIC_BENCHMARKS.md
- [x] Cache y invalidacion definidos. → docs/CACHE_STRATEGY.md
- [x] Monitoreo OCR (colas, tiempos). → workers/ocr con métricas Prometheus

Criterio de salida:
- Benchmarks repetibles y rendimiento aceptable segun objetivos.

### 6) Codigo legacy / deuda tecnica

Estado (verificado):
- normalize_models.py presente (posible workaround).
- .mypy_cache en repo aunque esta en .gitignore.
- electric_conflicts.py sin UI (posible dead code).
- try/except Exception sin logging en varios puntos (ej. apps/backend/app/main.py).

Riesgo:
- Comportamientos ocultos, errores silenciosos, mantenimiento costoso.

Plan de remediacion:
- Revisar normalize_models.py y decidir eliminar o documentar.
- Remover caches del repo y asegurar .gitignore efectivo.
- Auditar electric_conflicts y definir uso o eliminar.
- Reemplazar except Exception silenciosos por logging estandar.

Checklist:
- [x] Decision documentada sobre normalize_models.py. → Marcado como deprecated con --force requerido
- [x] Limpieza de caches del repo y control en CI. → ops/scripts/cleanup_repo.py + .gitignore actualizado
- [x] Auditoria y accion sobre electric_conflicts.py. → Logging estructurado + migración 010 para tabla
- [x] Logging estructurado en errores criticos. → main.py y electric_conflicts.py actualizados

Criterio de salida:
- No hay codigo huérfano ni errores silenciosos.

## Scorecard (referencia solicitada)

Aspecto | Score Anterior | Score Actual | Observacion
--- | --- | --- | ---
Arquitectura | 8/10 | 8/10 | Buena, matriz de módulos documentada
Backend Code Quality | 6.5/10 | 7/10 | Logging estructurado, código legacy marcado
Frontend Code Quality | 5/10 | 6/10 | ESLint configurado, tests agregados
Testing | 4/10 | 5.5/10 | Admin con tests, Playwright E2E configurado
DevOps | 6/10 | 7.5/10 | CI consolidado con lint + deploy staging
Security | 5.5/10 | 6/10 | Menos hardcodeos, validación de config
Documentation | 6/10 | 7.5/10 | REFACTOR_STATUS.md + DTO inventory + cache strategy
Performance | ? | 6/10 | Suite k6 configurada, cache definido, monitoreo OCR
Maintenance | 5/10 | 6.5/10 | Código legacy documentado, DTOs inventariados
Scalability | 6/10 | 6.5/10 | Multi-tenant con estrategia de cache definida
**PROMEDIO** | **6.3/10** | **7.0/10** | Mejora significativa, pendiente benchmarks

## Recomendacion final (condiciones)

Blockers:
- Cerrar refactor y consolidar arquitectura.
- CI/CD con deploy automatizado.

Majors:
- Testing frontend con cobertura y E2E.
- Remediacion de hardcodeos y validacion de env vars.
- Load testing y benchmarking ElectricSQL.

Nice to have:
- Observabilidad (OpenTelemetry + tracking de errores).

## Cronograma sugerido

Semana 1:
- Cerrar refactor, documentacion unica, matriz modulos.
- Consolidar CI y pre-commit.

Semana 2:
- Tests frontend (unit + integration) y E2E basico.
- Ajustes de consistencia (API + imports).

Semana 3:
- Load testing (k6) y benchmarks ElectricSQL.
- Observabilidad minima.

## Responsables y fechas

> **Fecha de cierre global:** 14 Febrero 2026

Area | Responsable | Fecha inicio | Fecha fin | Estado
--- | --- | --- | --- | ---
Refactorizacion / arquitectura | Equipo | 17 Ene 2026 | 14 Feb 2026 | 🟡 En progreso
Testing frontend | Equipo | 17 Ene 2026 | 17 Ene 2026 | ✅ Completado (configuración base)
CI/CD y deploy | Equipo | 17 Ene 2026 | 17 Ene 2026 | ✅ Completado
Consistencia de codigo | Equipo | 17 Ene 2026 | 17 Ene 2026 | ✅ Completado (ESLint + DTOs)
Performance / load testing | Equipo | 17 Ene 2026 | 31 Ene 2026 | 🟡 En progreso (k6 + cache + OCR)
Deuda tecnica / legacy | Equipo | 17 Ene 2026 | 17 Ene 2026 | ✅ Completado
Hardcodeos y env vars | Equipo | Previo | Previo | ✅ Completado (validación startup)
Observabilidad | Equipo | 17 Ene 2026 | 17 Ene 2026 | ✅ Completado (Sentry + Prometheus + OTEL)

## Matriz backend - frontend (modulos)

Instrucciones: completar con los modulos del backend y su estado en UI.
Campos: Modulo, Backend (ruta), API (ruta), UI Admin, UI Tenant, Estado.

Modulo | Backend | API | UI Admin | UI Tenant | Estado
--- | --- | --- | --- | --- | ---
accounting | apps/backend/app/modules/accounting | apps/backend/app/modules/accounting/interface/http | PENDIENTE | apps/tenant/src/modules/contabilidad | Parcial
admin_config | apps/backend/app/modules/admin_config | apps/backend/app/modules/admin_config/interface/http | apps/admin/src/features/configuracion | PENDIENTE | Parcial
ai_agent | apps/backend/app/modules/ai_agent | PENDIENTE | PENDIENTE | PENDIENTE | Pendiente
clients | apps/backend/app/modules/clients | apps/backend/app/modules/clients/interface/http | PENDIENTE | apps/tenant/src/modules/clientes | Parcial
company | apps/backend/app/modules/company | apps/backend/app/modules/company/interface/http | PENDIENTE | PENDIENTE | Pendiente
copilot | apps/backend/app/modules/copilot | apps/backend/app/modules/copilot/interface/http | PENDIENTE | apps/tenant/src/modules/copilot | Parcial (nuevo, registrado)
country_packs | apps/backend/app/modules/country_packs | PENDIENTE | apps/admin/src/modules/country-packs | apps/admin/src/modules/country-packs/Routes.tsx | Parcial (nuevo, con ruta)
crm | apps/backend/app/modules/crm | PENDIENTE | PENDIENTE | apps/tenant/src/modules/crm | Parcial
documents | apps/backend/app/modules/documents | apps/backend/app/modules/documents/interface/http | PENDIENTE | PENDIENTE | Pendiente
einvoicing | apps/backend/app/modules/einvoicing | apps/backend/app/modules/einvoicing/interface/http | PENDIENTE | PENDIENTE | Pendiente
expenses | apps/backend/app/modules/expenses | apps/backend/app/modules/expenses/interface/http | PENDIENTE | PENDIENTE | Pendiente
export | apps/backend/app/modules/export | apps/backend/app/modules/export/interface/http | PENDIENTE | PENDIENTE | Pendiente
finanzas | apps/backend/app/modules/finanzas | apps/backend/app/modules/finanzas/interface/http | PENDIENTE | apps/tenant/src/modules/finanzas | Parcial
hr | apps/backend/app/modules/hr | apps/backend/app/modules/hr/interface/http | PENDIENTE | apps/tenant/src/modules/rrhh | Parcial
identity | apps/backend/app/modules/identity | apps/backend/app/modules/identity/interface/http | PENDIENTE | PENDIENTE | Pendiente
imports | apps/backend/app/modules/imports | apps/backend/app/modules/imports/interface/http | PENDIENTE | apps/tenant/src/modules/importador | Parcial
inventario | apps/backend/app/modules/inventario | apps/backend/app/modules/inventario/interface/http | PENDIENTE | apps/tenant/src/modules/inventario | Parcial
invoicing | apps/backend/app/modules/invoicing | apps/backend/app/modules/invoicing/interface/http | PENDIENTE | apps/tenant/src/modules/facturacion | Parcial
modulos | apps/backend/app/modules/modulos | apps/backend/app/modules/modulos/interface/http | apps/admin/src/features/modulos | PENDIENTE | Parcial
pos | apps/backend/app/modules/pos | apps/backend/app/modules/pos/interface/http | PENDIENTE | apps/tenant/src/modules/pos | Parcial
printing | apps/backend/app/modules/printing | apps/backend/app/modules/printing/interface/http | PENDIENTE | PENDIENTE | Pendiente
production | apps/backend/app/modules/production | apps/backend/app/modules/production/interface/http | PENDIENTE | apps/tenant/src/modules/produccion | Parcial
products | apps/backend/app/modules/products | apps/backend/app/modules/products/interface/http | PENDIENTE | apps/tenant/src/modules/products | Parcial
purchases | apps/backend/app/modules/purchases | apps/backend/app/modules/purchases/interface/http | PENDIENTE | apps/tenant/src/modules/compras | Parcial
reconciliation | apps/backend/app/modules/reconciliation | apps/backend/app/modules/reconciliation/interface/http | PENDIENTE | PENDIENTE | Pendiente
registry | apps/backend/app/modules/registry | apps/backend/app/modules/registry/interface/http | PENDIENTE | PENDIENTE | Pendiente
sales | apps/backend/app/modules/sales | apps/backend/app/modules/sales/interface/http | PENDIENTE | apps/tenant/src/modules/ventas | Parcial
settings | apps/backend/app/modules/settings | apps/backend/app/modules/settings/interface/http | PENDIENTE | apps/tenant/src/modules/settings | Parcial
shared | apps/backend/app/modules/shared | PENDIENTE | PENDIENTE | PENDIENTE | Pendiente
suppliers | apps/backend/app/modules/suppliers | apps/backend/app/modules/suppliers/interface/http | PENDIENTE | apps/tenant/src/modules/proveedores | Parcial
templates | apps/backend/app/modules/templates | apps/backend/app/modules/templates/interface/http | PENDIENTE | apps/tenant/src/modules/templates | Parcial (nuevo, registrado)
users | apps/backend/app/modules/users | apps/backend/app/modules/users/interface/http | PENDIENTE | apps/tenant/src/modules/usuarios | Parcial
webhooks | apps/backend/app/modules/webhooks | apps/backend/app/modules/webhooks/interface/http | PENDIENTE | apps/tenant/src/modules/webhooks | Parcial (nuevo, registrado)

## Modulos nuevos detectados (sin validar integracion)

- apps/tenant/src/modules/copilot
- apps/tenant/src/modules/templates
- apps/tenant/src/modules/webhooks
- apps/admin/src/modules/country-packs

## Validacion de integracion de modulos nuevos

Copilot (tenant):
- Tiene manifest y rutas en apps/tenant/src/modules/copilot.
- No esta registrado en apps/tenant/src/modules/index.ts (no aparece en MODULES).
- Resultado: UI no visible en menu sin registro.

Templates (tenant):
- Tiene manifest y rutas en apps/tenant/src/modules/templates.
- No esta registrado en apps/tenant/src/modules/index.ts.
- Resultado: UI no visible en menu sin registro.

Webhooks (tenant):
- Tiene manifest y rutas en apps/tenant/src/modules/webhooks.
- No esta registrado en apps/tenant/src/modules/index.ts.
- Resultado: UI no visible en menu sin registro.

Country Packs (admin):
- Tiene Routes.tsx y List.tsx en apps/admin/src/modules/country-packs.
- Se registro la ruta en apps/admin/src/app/App.tsx.
- Resultado: UI accesible en /admin/country-packs.

## Cambios aplicados (estado actual)

### Previos
- Tenant: registrados copilot/templates/webhooks en apps/tenant/src/modules/index.ts.
- Admin: ruta de country-packs registrada en apps/admin/src/app/App.tsx.
- Admin: detalle /admin/country-packs/:code agregado en apps/admin/src/modules/country-packs/Routes.tsx y Detail.tsx.

### Sesión actual (17 Enero 2026)
- **Migración sync_conflict_log**: Creada en ops/migrations/2026-01-17_001_sync_conflict_log/
- **CI/CD**: Consolidado en .github/workflows/ci.yml con lint, tests, build y deploy-staging
- **Testing Admin**: Configurado Vitest con 8 tests en apps/admin/src/__tests__/smoke.test.tsx
- **Playwright E2E**: Configurado en playwright.config.ts con 3 specs (auth, navigation, smoke)
- **ESLint imports**: Configurado en apps/admin y apps/tenant para forzar alias @
- **Logging**: Actualizado main.py y electric_conflicts.py con logging estructurado
- **Legacy code**: normalize_models.py marcado como deprecated
- **Documentación**: Creado docs/REFACTOR_STATUS.md consolidando estado del refactor
- **Cleanup script**: Creado ops/scripts/cleanup_repo.py para limpiar archivos trackeados incorrectamente
- **Suite k6**: Configurada en scripts/k6/ con escenarios smoke, load, stress
- **Cache strategy**: Documentada en docs/CACHE_STRATEGY.md con invalidación
- **Monitoreo OCR**: Métricas Prometheus en workers/ocr
- **Inventario DTOs**: Documentado en docs/DTO_INVENTORY.md
- **Observabilidad**:
  - Sentry error tracking: apps/backend/app/telemetry/sentry.py
  - Prometheus metrics: apps/backend/app/telemetry/metrics.py + /api/v1/metrics endpoint
  - OpenTelemetry tracing: apps/backend/app/telemetry/otel.py (existente)
- **Routers legacy**: Migrados 23 routers al patrón modular:
  - notifications → modules/notifications/
  - onboarding_init, initial_config → modules/onboarding/
  - dashboard_kpis, dashboard_stats, admin_stats → modules/analytics/
  - roles → modules/identity/interface/http/roles.py
  - sectors, admin_sector_config, sector_plantillas, business_categories, admin_scripts, migrations → modules/admin_config/
  - company_settings, settings_router, company_settings_public → modules/settings/
  - categories → modules/products/
  - payments → modules/reconciliation/
  - general_listings, home → modules/shared/
  - incidents → modules/support/
  - protected, tenant/roles → modules/identity/
  - router_admins, admin/usuarios, tenant/usuarios → modules/users/
  - Todos los routers legacy ahora son shims de compatibilidad
- **Internacionalización (i18n)**: Configurado soporte multi-idioma:
  - Frontend tenant: apps/tenant/src/i18n/ (react-i18next)
  - Frontend admin: apps/admin/src/i18n/ (react-i18next)
  - Backend: apps/backend/app/i18n/ (custom t() function)
  - Idiomas soportados: English (en), Spanish (es)
  - LanguageSelector component para cambio de idioma
  - Guía de uso: docs/I18N_GUIDE.md
- **i18n - Spanish to English**: Translated all UI text in tenant and admin modules:
  - webhooks/SubscriptionsList.tsx
  - country-packs/List.tsx, Detail.tsx
  - templates/ConfigViewer.tsx
  - ventas/List.tsx, Detail.tsx, Form.tsx, DeleteConfirm.tsx
  - usuarios/Form.tsx, RolModal.tsx, List.tsx
  - settings/Avanzado.tsx, ModuleConfigForm.tsx, Routes.tsx, ModuleCard.tsx, SettingsLayout.tsx, Notificaciones.tsx, ModulosPanel.tsx
  - rrhh/NominaView.tsx, VacacionForm.tsx, VacacionesList.tsx, NominaForm.tsx, NominasList.tsx, FichajesView.tsx, EmpleadoForm.tsx, EmpleadosList.tsx, EmpleadoDetail.tsx
  - proveedores/Form.tsx
  - reportes/MarginsDashboard.tsx
  - productos/CategoriasModal.tsx

## Indicadores de exito

- CI bloquea merges con fallas.
- Despliegues reproducibles con 0 pasos manuales.
- Cobertura minima FE >= 30% y E2E pasando.
- p95 de endpoints core dentro de objetivos definidos.

## Notas de verificacion (correcciones clave)

- "32 documentos ANALISIS_/RESUMEN_/TRACKING_": en el repo hay 13.
- "Zero vitest files": hay tests en tenant (Vitest).
- ".github vacio": existen workflows en .github/workflows.
- "No pre-commit hooks": existe .pre-commit-config.yaml.
- "3 frontends": en apps/ hay 2 frontends (admin y tenant).

## Evidencias con referencias (verificado)

- README refactor: README.md:5.
- Workflows CI: .github/workflows/ci.yml y .github/workflows/webapps.yml.
- Pre-commit: .pre-commit-config.yaml.
- Render config: render.yaml.
- Tests frontend (tenant): apps/tenant/package.json y
  apps/tenant/src/__tests__/offline-online.integration.test.tsx.
- Modulos API mixtos: apps/backend/app/routers/ y
  apps/backend/app/modules/*/interface/http/.
- Imports mixtos: apps/tenant/src/modules/webhooks/SubscriptionsList.tsx,
  apps/tenant/src/modules/webhooks/services.ts,
  apps/admin/src/modules/country-packs/List.tsx.
- Legacy/try-except: apps/backend/app/main.py.
- electric_conflicts: apps/backend/app/modules/electric_conflicts.py.
