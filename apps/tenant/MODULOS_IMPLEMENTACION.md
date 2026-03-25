# Implementación de Permisos & i18n - 6 Módulos Restantes

## Patrón a Aplicar (copiar/pegar)

### 1. Imports en `List.tsx` (o principal component)
```typescript
import { useTranslation } from 'react-i18next'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'

export default function ModuleList() {
  const { t } = useTranslation(['module', 'common'])
  const can = usePermission()
```

### 2. Gate Global (antes del return)
```typescript
  if (!can('module:read')) {
    return <PermissionDenied permission="module:read" />
  }
```

### 3. Permisos en Botones
```typescript
{can('module:create') && <button>...</button>}
{can('module:update') && <Link>Edit</Link>}
{can('module:delete') && <button onClick={handleDelete}>Delete</button>}
```

### 4. Localizar Textos (buscar/reemplazar)
- Títulos: `"Title"` → `t('module:title')`
- Botones: `"New"` → `t('module:new')`
- Headers: `"Name"` → `t('module:table.name')`
- Placeholders: `"Search..."` → `t('module:search')`
- Mensajes: `"Deleted"` → `t('module:messages.deleted')`
- Empty: `"No records"` → `t('module:empty')`

### 5. Crear Locales
```bash
touch apps/tenant/src/locales/en/MODULE.json
touch apps/tenant/src/locales/es/MODULE.json
```

---

## 📋 Checklist por Módulo

### 1. **Finances**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `finances:read`, `finances:create`, `finances:update`, `finances:delete`
**Locales a crear:** `en/finances.json`, `es/finances.json`

Busca en List.tsx:
- [ ] Añadir imports (useTranslation, usePermission, PermissionDenied)
- [ ] Agregar hooks: `const { t } = useTranslation(['finances', 'common'])`; `const can = usePermission()`
- [ ] Gate global: `if (!can('finances:read')) return <PermissionDenied...`
- [ ] Localizar títulos, headers, botones, mensajes
- [ ] Envolver botones con `can('finances:...')`
- [ ] Crear en/es json con claves necesarias

**Claves mínimas:**
```json
{
  "title": "...",
  "new": "...",
  "empty": "...",
  "table": { "date": "...", "amount": "...", "description": "..." },
  "messages": { "deleted": "..." },
  "confirmDelete": "..."
}
```

---

### 2. **Accounting**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `accounting:read`, `accounting:create`, `accounting:update`, `accounting:delete`
**Locales:** `en/accounting.json`, `es/accounting.json`

Mismo proceso que Finances.

---

### 3. **POS**
**Archivos:** `List.tsx` (o `Sales.tsx`), `Routes.tsx`
**Permisos:** `pos:read`, `pos:create`, `pos:update`, `pos:delete`
**Locales:** `en/pos.json`, `es/pos.json`

Mismo proceso.

---

### 4. **Importer**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `importer:read`, `importer:create`, `importer:delete`
**Locales:** `en/importer.json`, `es/importer.json`

Mismo proceso (probablemente solo create/delete, no update).

---

### 5. **Settings**
**Archivos:** `Panel.tsx` o `Settings.tsx`, `Routes.tsx`
**Permisos:** `settings:read`, `settings:update`
**Locales:** `en/settings.json`, `es/settings.json`

Mismo proceso (probablemente solo read/update).

---

### 6. **Reportes**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `reportes:read`, `reportes:create`, `reportes:delete`
**Locales:** `en/reportes.json`, `es/reportes.json`

Mismo proceso.

---

### 7. **CRM / Producción**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `crm:read`, `crm:create`, `crm:update`, `crm:delete`
**Locales:** `en/crm.json`, `es/crm.json`

Mismo proceso.

---

### 8. **RimayPilot / Templates**
**Archivos:** `List.tsx`, `Routes.tsx`
**Permisos:** `templates:read`, `templates:create`, `templates:update`, `templates:delete`
**Locales:** `en/templates.json`, `es/templates.json`

Mismo proceso.

---

## 🚀 Comando de Búsqueda Rápido

Para cada módulo, usa Find & Replace en VS Code:

1. **Busca hardcoded:**
   - `"New ` → reemplazar por `{t('module:new')}`
   - `"Delete` → reemplazar por `{t('common.delete')}`
   - Etc.

2. **Verifica Routes.tsx:**
   - Asegúrate de que `ProtectedRoute` tenga el permiso correcto
   - `permission="module:read"` en el wrapper global
   - `permission="module:create"`, `module:update`, `module:delete` en rutas específicas

---

## ✅ Verificación Final

Para cada módulo, antes de commitear:

- [ ] Archivo `List.tsx` tiene gate global `if (!can('module:read'))`
- [ ] Botones tienen `{can('module:...')}`
- [ ] No hay strings hardcoded (todo es `t('module:...')`
- [ ] `en/module.json` existe con todas las claves
- [ ] `es/module.json` existe con traducción
- [ ] `Routes.tsx` tiene `ProtectedRoute` correctos

---

## 📝 Template JSON Completo

```json
{
  "title": "Module Title",
  "subtitle": "Subtitle...",
  "new": "New Item",
  "edit": "Edit",
  "delete": "Delete",
  "empty": "No records found",
  "loading": "Loading...",
  "search": "Search...",
  "searchPlaceholder": "Search by name...",
  "confirmDelete": "Are you sure?",
  "filters": {
    "all": "All",
    "active": "Active",
    "inactive": "Inactive"
  },
  "status": {
    "active": "Active",
    "inactive": "Inactive"
  },
  "table": {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "date": "Date",
    "amount": "Amount",
    "status": "Status"
  },
  "messages": {
    "created": "Item created",
    "updated": "Item updated",
    "deleted": "Item deleted"
  }
}
```

---

## ⏱️ Tiempo Estimado

- **Por módulo:** 5-10 minutos
- **Total 6 módulos:** 30-60 minutos
- **Más rápido si:** usas Find & Replace y sigues el patrón exacto

---

## 💡 Consejos

1. **Abre 2 tabs:** Uno con `List.tsx` y otro con `en/module.json`
2. **Copia botones:** Si tienes un módulo hecho bien (ej: Expenses), copia la estructura
3. **Busca patrones comunes:**
   - `"New Xxxx"` → siempre es `module:new`
   - `"Delete"` → siempre es `common.delete`
   - `"Loading"` → siempre es `common.loading`

4. **Valida con TypeScript:** Si ves errores en rojo, revisa que las claves de `t()` existan en los JSON

---

## 🔗 Referencias Completadas

- ✅ Inventory: `StockList.tsx`, `MovementForm.tsx`, `MovementFormBulk.tsx`
- ✅ Expenses: `List.tsx`
- ✅ Customers: `List.tsx`
- ✅ Suppliers: `List.tsx`
