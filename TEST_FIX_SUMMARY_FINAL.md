# Resumen de Correcciones de Tests - Estado Final

## ✅ Corregido

### 1. **conftest.py** - JWT Tokens con user_id
- **Archivo**: `apps/backend/app/tests/conftest.py`
- **Línea 477**: Añadido `"user_id": user_id` al payload JWT
- **Motivo**: `get_current_user()` en `middleware/tenant.py` requiere este claim

### 2. **conftest.py** - Tablas Stub SQLite (POS + E-invoicing)
- **Archivo**: `apps/backend/app/tests/conftest.py`
- **Líneas 228-382**: Creadas tablas stub SQLite-compatible:
  - `pos_registers`, `pos_shifts`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`
  - `doc_series`, `store_credits`
  - `einv_credentials`, `sri_submissions`
- **Líneas 103-116**: Excluidas estas tablas de metadata para evitar compilación con sintaxis PG

### 3. **test_integration_excel_erp.py** - PermissionError Windows
- **Archivo**: `apps/backend/app/tests/test_integration_excel_erp.py`
- **Líneas 33, 76**: Añadido `wb.close()` antes de `wb.save()`
- **Motivo**: openpyxl no cierra archivos automáticamente en Windows

### 4. **pos.py** - Endpoint POST /registers + SQLite Compatibility
- **Archivo**: `apps/backend/app/routers/pos.py`
- **Líneas 28-31**: Función `is_sqlite()` para detectar DB tipo
- **Líneas 129-186**: Nuevo endpoint `POST /api/v1/pos/registers`
- **Líneas 194-225**: Modificado `GET /registers` con lógica condicional SQLite/PostgreSQL
- **Motivo**: Tests necesitan crear registers; sintaxis `::text` no funciona en SQLite

### 5. **pos.py** - Corrección de Indentación
- **Archivo**: `apps/backend/app/routers/pos.py`
- **Líneas 1158-1187**: Corregida indentación de función `print_receipt()`
- **Motivo**: Error de sintaxis Python impedía montar el router

## ⚠️ PROBLEMA PENDIENTE: 403 Forbidden

### Síntoma
Todos los tests POS/einvoicing/imports_limits dan error **403 "forbidden"** aunque:
- ✅ Router POS se monta correctamente (`[INFO] app.router: POS router mounted at /api/v1/pos`)
- ✅ JWT token tiene `user_id` claim
- ✅ Headers de autenticación se generan correctamente

### Causa Raíz
El problema está en **`middleware/tenant.py:ensure_tenant()`**:

1. **Línea 46**: `with_access_claims(request)` valida el JWT
2. **Línea 48**: Extrae `claim_tid = claims.get("tenant_id")`
3. **Línea 28-32**: `_resolve_tenant_uuid()` intenta buscar el tenant en la DB:
   ```python
   if tid.isdigit():
       row = db.execute(text("SELECT id::text FROM tenants WHERE empresa_id=:eid"), {"eid": int(tid)}).first()
       if not row or not row[0]:
           raise HTTPException(status_code=403, detail="tenant_not_found")
   ```

**El problema**: El `tenant_id` en el JWT generado por los tests **NO existe en la tabla `tenants`**.  
Los tests generan un `uuid4()` aleatorio y lo pasan al token, pero nunca crean el registro correspondiente en la BD.

### Solución

**Opción 1** (Rápida - Bypass en desarrollo):
Modificar `middleware/tenant.py:ensure_tenant()` para que en tests/SQLite acepte tenant_id sin validar:

```python
def ensure_tenant(request: Request, db: Session = Depends(get_db)) -> str:
    # ... código existente ...
    
    # Test/SQLite bypass: accept any valid UUID without DB validation
    if is_sqlite() or str(getattr(settings, "ENV", "development")).lower() != "production":
        if claim_tid and not claim_tid.isdigit():
            # Assume it's a valid UUID, skip DB validation
            tenant_uuid = str(claim_tid)
            set_tenant_guc(db, tenant_uuid, persist=False)
            return tenant_uuid
    
    # Production: validate normally
    tenant_uuid = _resolve_tenant_uuid(claim_tid, db)
    # ... resto del código ...
```

**Opción 2** (Correcta - Crear tenant en fixtures):
Modificar `conftest.py:auth_headers()` para que cree automáticamente el tenant:

```python
@pytest.fixture
def auth_headers(jwt_token_factory, db):
    """Headers de autenticación con token JWT válido."""
    def _create(tenant_id: str | None = None, **token_kwargs):
        if not tenant_id:
            tenant_id = str(uuid.uuid4())
        
        # Asegurar que el tenant existe en DB (para tests)
        db.execute(
            text("INSERT OR IGNORE INTO tenants (id, empresa_id, slug, country_code, base_currency) VALUES (:id, 1, 'test-tenant', 'ES', 'EUR')"),
            {"id": tenant_id}
        )
        db.commit()
        
        token = jwt_token_factory(tenant_id=tenant_id, **token_kwargs)
        headers = {"Authorization": f"Bearer {token}"}
        headers["X-Tenant-ID"] = tenant_id
        return headers
    
    return _create
```

## 🔧 Próximos Pasos (Orden de Prioridad)

1. **Implementar Opción 2**: Modificar `conftest.py:auth_headers()` para crear tenant automáticamente
2. **Ejecutar test_pos_complete.py**: Verificar que pasa el flujo completo
3. **Ejecutar test_einvoicing.py**: Verificar compatibilidad einv_credentials
4. **Ejecutar test_imports_limits.py**: Verificar que pasa con permisos adecuados
5. **Revisar sintaxis SQLite**: Buscar más queries con `::jsonb` o `::text` y agregar lógica condicional
6. **Ejecutar suite completa**: `pytest app/tests/ -v`

## 📊 Estado de Tests

| Test | Estado | Problema | Solución |
|------|--------|----------|----------|
| `test_pos_complete.py` | ❌ 403 | tenant_id no existe en DB | Crear tenant en auth_headers |
| `test_einvoicing.py` | ❌ 403 (probablemente) | Mismo problema | Misma solución |
| `test_integration_excel_erp.py` | ✅ Corregido | PermissionError Windows | wb.close() implementado |
| `test_imports_limits.py` | ❌ 403 (probablemente) | Mismo problema | Misma solución |

## 📝 Notas de Implementación

### Sintaxis SQL SQLite vs PostgreSQL

**PostgreSQL**:
```sql
SELECT id::text, tenant_id::text, metadata::jsonb
```

**SQLite** (compatible):
```sql
SELECT id, tenant_id, metadata
```

**Solución implementada**:
```python
if is_sqlite():
    query = text("SELECT id FROM table WHERE tenant_id = :tid")
else:
    query = text("SELECT id::text FROM table WHERE tenant_id::text = :tid")
```

### Consideraciones de Seguridad

⚠️ **IMPORTANTE**: El bypass de validación de tenant en desarrollo/tests **DEBE** estar protegido con:
```python
if str(getattr(settings, "ENV", "development")).lower() != "production":
    # bypass code
```

Nunca debe llegar a producción sin validación de tenant adecuada.

---

**Última actualización**: 2025-01-24  
**Estado**: Correcciones parciales implementadas, pendiente fix 403 en auth_headers
