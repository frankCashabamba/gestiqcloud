# ✅ Función Eliminar Productos del Importador

## 🎯 Problema Resuelto

**ANTES:** No había forma de eliminar productos duplicados o incorrectos antes de promoverlos al catálogo.

**AHORA:** Botón rojo "Eliminar (X)" que permite borrar productos seleccionados del importador.

---

## 📦 Implementación

### Backend (2 Endpoints Nuevos)

#### 1. DELETE `/api/v1/imports/batches/{batch_id}/items/{item_id}`
Elimina un item individual del batch.

```python
@router.delete("/batches/{batch_id}/items/{item_id}")
def delete_batch_item_endpoint(
    batch_id: UUID,
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Elimina un item del batch"""
    # Verificar tenant y permisos
    # Eliminar item
    db.delete(item)
    db.commit()
    return {"status": "ok", "message": "Item eliminado"}
```

**Ejemplo:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/imports/batches/{batch_id}/items/{item_id}" \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. POST `/api/v1/imports/items/delete-multiple`
Elimina múltiples items en una sola llamada.

```python
@router.post("/items/delete-multiple")
def delete_multiple_items_endpoint(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Elimina múltiples items por sus IDs"""
    item_ids = payload.get("item_ids", [])
    
    deleted = db.query(ImportItem).filter(
        ImportItem.id.in_(uuid_ids),
        ImportItem.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    
    return {
        "status": "ok",
        "deleted": deleted,
        "message": f"{deleted} items eliminados"
    }
```

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/imports/items/delete-multiple" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": ["uuid1", "uuid2", "uuid3"]
  }'
```

---

### Frontend (Botón + Handler)

#### Botón de Eliminar
```tsx
<button
  onClick={handleEliminar}
  disabled={selectedIds.size === 0}
  className="px-4 py-2 bg-rose-600 text-white rounded hover:bg-rose-700 
             disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
>
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
  Eliminar ({selectedIds.size})
</button>
```

#### Handler
```tsx
const handleEliminar = async () => {
  if (selectedIds.size === 0) {
    alert('Selecciona al menos un producto')
    return
  }

  if (!confirm(`¿Eliminar ${selectedIds.size} productos? Esta acción no se puede deshacer.`)) 
    return

  try {
    const res = await fetch('/api/v1/imports/items/delete-multiple', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        item_ids: Array.from(selectedIds),
      }),
    })

    if (!res.ok) throw new Error('Error al eliminar')

    const result = await res.json()
    alert(`✅ ${result.deleted} productos eliminados`)
    
    setSelectedIds(new Set())
    fetchProductos()
  } catch (err: any) {
    alert(`Error: ${err.message}`)
  }
}
```

---

## 🎨 UI Final

```
┌──────────────────────────────────────────────────────────────┐
│  Productos del Lote                                          │
│  150 productos · 5 seleccionados                             │
│                                                              │
│  [🗑️ Eliminar (5)]  [✓ Promover (5)]                        │
└──────────────────────────────────────────────────────────────┘
│  ☑ Código    Nombre       Precio    Stock    Categoría      │
├──────────────────────────────────────────────────────────────┤
│  ☑ 001       Pan          €0.50     100      Panadería       │
│  ☐ 002       Leche        €1.20     50       Lácteos         │
│  ☑ 003       Yogurt       €0.80     30       Lácteos         │
│  ☑ 003       Yogurt DUP   €0.80     30       Lácteos    ← Duplicado
│  ☐ 004       Mantequilla  €2.50     20       Lácteos         │
└──────────────────────────────────────────────────────────────┘
```

**Flujo:**
1. Usuario selecciona productos (checkboxes)
2. Click en **"Eliminar (X)"**
3. Confirmación: "¿Eliminar 5 productos? Esta acción no se puede deshacer."
4. ✅ Productos eliminados
5. Lista se actualiza automáticamente

---

## ✅ Casos de Uso

### 1. Eliminar Duplicados
```
Problema: Importaste 2 veces el mismo archivo
Solución:
1. Seleccionar productos duplicados
2. Click "Eliminar"
3. Solo quedan productos únicos
```

### 2. Corregir Errores
```
Problema: Algunos productos tienen datos incorrectos
Solución:
1. Seleccionar productos erróneos
2. Click "Eliminar"
3. Re-importar con datos correctos
```

### 3. Filtrar Productos
```
Problema: El Excel tiene productos que no quieres importar
Solución:
1. Seleccionar productos no deseados
2. Click "Eliminar"
3. Solo promover los que sí quieres
```

---

## 🔒 Seguridad

- ✅ Verificación de tenant_id (RLS)
- ✅ Confirmación antes de eliminar
- ✅ Validación de permisos
- ✅ Eliminación física (no soft delete)
- ✅ Mensaje de éxito/error

---

## 📊 Testing

### Test Manual
```bash
# 1. Importar archivo con duplicados
curl -X POST "http://localhost:8000/api/v1/imports/batches" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"source_type": "productos", "origin": "test"}'

# 2. Ver productos
curl "http://localhost:8000/api/v1/imports/batches/{batch_id}/items/products" \
  -H "Authorization: Bearer $TOKEN"

# 3. Eliminar productos
curl -X POST "http://localhost:8000/api/v1/imports/items/delete-multiple" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"item_ids": ["uuid1", "uuid2"]}'

# 4. Verificar que se eliminaron
curl "http://localhost:8000/api/v1/imports/batches/{batch_id}/items/products" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📝 Archivos Modificados

1. **Backend:**
   - `apps/backend/app/modules/imports/interface/http/tenant.py` (+70 líneas)

2. **Frontend:**
   - `apps/tenant/src/modules/importador/ProductosImportados.tsx` (+40 líneas)

**Total:** 2 archivos, ~110 líneas nuevas

---

## ✨ Estado

- ✅ Backend endpoints implementados
- ✅ Frontend botón + handler
- ✅ UI profesional con iconos
- ✅ Confirmación de seguridad
- ✅ Actualización automática

**Estado:** 🚀 **LISTO PARA PRODUCCIÓN**

---

**Fecha:** 28 Octubre 2025  
**Versión:** 1.0.0
