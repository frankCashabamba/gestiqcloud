# Migración: importador → imports

## Estado
Backend ya usa `/api/v1/imports` ✓

Frontend necesita estandarización a inglés.

## Pasos

### 1. Cerrar VSCode completamente
```bash
# Cerrar todos los editores y VSCode
```

### 2. Renombrar carpeta (PowerShell como Admin)
```powershell
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto
Move-Item -Path "apps\tenant\src\modules\importador" -Destination "apps\tenant\src\modules\imports" -Force
```

### 3. Actualizar referencias en main.tsx
```typescript
// apps/tenant/src/main.tsx
// ANTES:
import { ImportQueueProvider } from './modules/importador/context/ImportQueueContext'
import ProcessingIndicator from './modules/importador/components/ProcessingIndicator'

// DESPUÉS:
import { ImportQueueProvider } from './modules/imports/context/ImportQueueContext'
import ProcessingIndicator from './modules/imports/components/ProcessingIndicator'
```

### 4. Actualizar slug del módulo en base de datos
```sql
-- Actualizar slug del módulo
UPDATE modules 
SET slug = 'imports' 
WHERE slug = 'importador';

-- Verificar
SELECT id, name, slug, icon FROM modules WHERE slug IN ('imports', 'importador');
```

### 5. Actualizar nombres de componentes internos (opcional pero recomendado)
Dentro de `apps/tenant/src/modules/imports/`:
- `ImportadorLayout.tsx` → `ImportsLayout.tsx`
- `ImportadorExcel.tsx` → `ImportsExcel.tsx`
- `ImportadorExcelWithQueue.tsx` → `ImportsExcelWithQueue.tsx`
- Etc.

### 6. Rutas finales
- Backend API: `http://localhost:8000/api/v1/imports/*`
- Frontend: `http://localhost:8082/kusi-panaderia/imports`

## Archivos a actualizar automáticamente

### apps/tenant/src/main.tsx
```diff
-import { ImportQueueProvider } from './modules/importador/context/ImportQueueContext'
-import ProcessingIndicator from './modules/importador/components/ProcessingIndicator'
+import { ImportQueueProvider } from './modules/imports/context/ImportQueueContext'
+import ProcessingIndicator from './modules/imports/components/ProcessingIndicator'
```

## Verificación
1. Levantar backend: `make dev`
2. Levantar frontend: `cd apps/tenant && npm run dev`
3. Navegar a: `http://localhost:8082/kusi-panaderia/imports`
4. Verificar que funcione el importador

## Rollback (si falla)
```sql
UPDATE modules SET slug = 'importador' WHERE slug = 'imports';
```

```powershell
Move-Item -Path "apps\tenant\src\modules\imports" -Destination "apps\tenant\src\modules\importador" -Force
```
