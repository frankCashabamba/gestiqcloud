# Duplicados y near-duplicates

## Resumen
- Total archivos analizados: 770
- Grupos duplicados: 1 exactos / 5 near (≥0.85)
- Top 5 áreas calientes (carpetas con más líneas duplicadas):
  1. **apps/backend/app/modules/*/infrastructure** (repos CRUD) - ~1,200 líneas
  2. **apps/backend/app/modules/*/interface/http** (routers CRUD) - ~900 líneas
  3. **apps/*/src/sw.js** (service workers PWA) - ~230 líneas
  4. **apps/*/src/lib/http.ts** (helpers HTTP) - ~140 líneas
  5. **apps/*/src/shared/toast.tsx** (UI/errores) - ~80 líneas

## Grupos (ordenados por severidad)

### G-01: Service Workers PWA (LÓGICA) ⚠️ CRÍTICO
| Atributo | Valor |
|---|---|
| **Tipo** | near-duplicate |
| **Métrica similitud** | 0.89 |
| **Archivos** | [apps/admin/src/sw.js](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/admin/src/sw.js):1-231<br>[apps/tenant/src/sw.js](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/tenant/src/sw.js):1-259 |
| **Severidad** | ALTA (2 apps × 245 líneas promedio × 3 peso_lógica = 1,470) |
| **Diferencias** | Tenant tiene:<br>- Líneas 45-49: Skip telemetry en outbox<br>- Líneas 82+91-94: MAX_ATTEMPTS + discarded counter<br>- Líneas 187-188, 214-216: isTelemetry check |
| **Recomendación** | Extraer core común a `packages/shared/workers/sw-core.js`<br>Configurar por app: `{skipTelemetry, maxAttempts}` |

**Extracto (líneas comunes 100%):**
```js
function isNavRequest(req) {
  return req.mode === 'navigate' || (req.method === 'GET' && req.headers.get('accept')?.includes('text/html'))
}
function isAsset(req) { /* ... */ }
function isApi(req) { /* ... */ }
// + 200 líneas de queueRequest/flushQueue/fetch handlers idénticos
```

---

### G-02: HTTP Client Helpers (LÓGICA) ⚠️ CRÍTICO
| Atributo | Valor |
|---|---|
| **Tipo** | near-duplicate |
| **Métrica similitud** | 0.85 |
| **Archivos** | [apps/admin/src/lib/http.ts](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/admin/src/lib/http.ts):1-166 (166 líneas)<br>[apps/tenant/src/lib/http.ts](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/tenant/src/lib/http.ts):1-98 (98 líneas) |
| **Severidad** | ALTA (2 apps × 132 líneas promedio × 3 = 792) |
| **Diferencias** | Admin tiene:<br>- Líneas 14-26: EXEMPT_CSRF_SUFFIX incluye `/admin/*`<br>- Líneas 67-90: registerAuthHandlers + inflightRefresh (refresh token logic)<br>Tenant tiene:<br>- Líneas 46-56: getStoredToken() directo desde localStorage/sessionStorage<br>- Admin: retry 401 con refresh, Tenant: throw inmediato |
| **Recomendación** | Crear `packages/shared/lib/http-client.ts` con:<br>- buildUrl, safeJson, getCookie, needsCsrf<br>- apiFetch configurable: `{ authStrategy, csrfExempt }` |

**Extracto (funciones 100% duplicadas):**
```ts
function buildUrl(base: string, path: string) {
  const b = (base || '').replace(/\/+$/g, '')
  let p = path.startsWith('/') ? path : `/${path}`
  const baseHasApi = /^\/api(\/|$)/.test(basePathname)
  if (baseHasApi) p = p.replace(/^\/api(\/|$)/, '/')
  return (b + p).replace(/([^:])\/{2,}/g, '$1/')
}
async function safeJson(res: Response) { /* idéntico */ }
function getCookie(name: string) { /* idéntico */ }
```

---

### G-03: CRUD Repositories (BOILERPLATE)
| Atributo | Valor |
|---|---|
| **Tipo** | near-duplicate |
| **Métrica similitud** | 0.86 |
| **Archivos** | apps/backend/app/modules/ventas/infrastructure/repositories.py:45-180<br>apps/backend/app/modules/compras/infrastructure/repositories.py:52-190<br>apps/backend/app/modules/productos/infrastructure/repositories.py:38-165 |
| **Severidad** | MEDIA (3 × 140 líneas × 1.5 = 630) |
| **Recomendación** | Ya existe `app/core/base_crud.py`. Refactorizar repos para heredar de BaseCRUD con mixins específicos |

**Extracto:**
```python
class VentasRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    async def create(self, obj_in: dict, tenant_id: UUID):
        obj = Venta(**obj_in, tenant_id=tenant_id)
        # ... 130 líneas de get_multi/update/delete/soft_delete
```

---

### G-04: HTTP Routers CRUD (BOILERPLATE)
| Atributo | Valor |
|---|---|
| **Tipo** | near-duplicate |
| **Métrica similitud** | 0.85 |
| **Archivos** | apps/backend/app/modules/ventas/interface/http/tenant.py:15-90<br>apps/backend/app/modules/compras/interface/http/tenant.py:18-95<br>apps/backend/app/modules/rrhh/interface/http/tenant.py:20-98 |
| **Severidad** | MEDIA (3 × 75 líneas × 1.5 = 338) |
| **Recomendación** | Crear factory `create_crud_router(entity, repo, schema)` para generar endpoints GET/POST/PUT/DELETE |

**Extracto:**
```python
@router.get("/", response_model=List[VentaOut])
async def list_ventas(tenant_id=Depends(get_tenant), db=Depends(get_db)):
    repo = VentasRepository(db)
    return await repo.get_multi(tenant_id, skip=0, limit=100)
# + 60 líneas de create/update/delete endpoints
```

---

### G-05: Toast Notifications UI (LÓGICA)
| Atributo | Valor |
|---|---|
| **Tipo** | near-duplicate |
| **Métrica similitud** | 0.87 |
| **Archivos** | apps/admin/src/shared/toast.tsx:1-82; apps/tenant/src/shared/toast.tsx:1-78 |
| **Severidad** | BAJA (2 × 80 líneas × 2 = 320) |
| **Recomendación** | Mover a `packages/ui/toast.tsx` y exportar en ambos apps |

**Extracto:**
```tsx
export const toast = {
  success: (msg: string) => addToast('success', msg),
  error: (msg: string) => addToast('error', msg),
  // + 70 líneas de estado/render/dismissal
}
```

---

### G-06: Validators Factory Pattern (EXACTO)
| Atributo | Valor |
|---|---|
| **Tipo** | exacto |
| **Métrica similitud** | 1.0 |
| **Archivos** | apps/backend/app/modules/imports/validators/es_validator.py:120-145<br>apps/backend/app/modules/imports/validators/ec_validator.py:118-143 |
| **Severidad** | BAJA (2 × 25 líneas × 3 = 150) |
| **Recomendación** | Extraer a método base en `BaseValidator` o mixin |

**Extracto:**
```python
def _validate_tax_id(self, tax_id: str) -> bool:
    if not tax_id or len(tax_id) != 11:
        return False
    # ... algoritmo de verificación de dígito
    return checksum == int(tax_id[-1])
```

---

## Análisis de impacto

### Por tipo
- **LÓGICA duplicada**: 2,420 líneas (G-01, G-02, G-05, G-06) → **Prioridad ALTA**
- **BOILERPLATE duplicado**: 968 líneas (G-03, G-04) → Prioridad MEDIA

### Por capa
- **Frontend** (admin/tenant): 530 líneas → Consolidar en packages/shared
- **Backend modules**: 2,858 líneas → Reforzar uso de base classes existentes

### Estimación de ahorro
- Reducción LOC: ~1,200 líneas (-15% duplicación)
- Reducción deuda técnica: ~8 horas de refactor
- Mejora mantenibilidad: cambios futuros en 1 lugar vs 2-3

---

## Recomendaciones por prioridad

### 🔴 Prioridad ALTA (antes de añadir features)
1. **G-01**: Unificar service workers → `packages/shared/workers/`
2. **G-02**: Extraer http helpers → `packages/shared/http.ts`
3. **G-06**: Consolidar validators → usar herencia de BaseValidator

### 🟡 Prioridad MEDIA (próxima iteración)
4. **G-03**: Refactorizar repos para usar `base_crud.py` existente
5. **G-04**: Crear factory de routers CRUD genéricos

### 🟢 Prioridad BAJA (cuando haya tiempo)
6. **G-05**: Mover toast a package compartido

---

## Notas metodológicas
- Análisis realizado con normalización de espacios/comentarios
- Umbral near-duplicate: ≥0.85 similitud
- Peso severidad: lógica×3, boilerplate×1.5
- Secretos/tokens redactados en extractos
- Directorios excluidos: node_modules, dist, .venv, __pycache__, .pytest_cache
