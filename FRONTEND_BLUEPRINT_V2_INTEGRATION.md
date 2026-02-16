# Frontend Blueprint V2 Integration — COMPLETADO

**Fecha**: 2026-02-14  
**Status**: ✅ CONECTADOS

---

## Resumen

Se actualizaron **3 componentes React** principales para conectar con las nuevas APIs Blueprint V2:

| API Backend | Componente Frontend | Status |
|---|---|---|
| `/api/v1/documents/storage/upload` | ImportadorExcelWithQueue.tsx | ✅ Conectado |
| `/api/v1/reports/product-margins` | MarginsDashboard.tsx | ✅ Conectado |
| `/api/v1/reports/profit` | PerdidasGanancias.tsx | ✅ Conectado |

---

## 1) Nuevo Servicio API — Document Storage

**Archivo**: `apps/tenant/src/services/api/documents.ts`

```typescript
export async function uploadDocument(
  file: File,
  docType: string = 'unknown',
  source: string = 'upload'
): Promise<DocumentUploadResponse>

export async function listDocuments(filters?: {...}): Promise<DocumentListItem[]>

export async function getDocument(documentId: string): Promise<Document>
```

**Cambios en ImportadorExcelWithQueue.tsx:**
- Importa `uploadDocument` desde el nuevo servicio
- En `handleFileChange()` y `handleDrop()` — ahora sube archivos a `/documents/storage/upload`
- Los archivos se registran con SHA256 deduplicación automática
- Mantiene compatibilidad con la cola de importación existente

---

## 2) Nuevo Servicio API — Profit Reports

**Archivo**: `apps/tenant/src/services/api/profit-reports.ts`

```typescript
export async function getProfitReport(
  dateFrom: string,
  dateTo: string
): Promise<ProfitReport>

export async function getProductMargins(
  dateFrom: string,
  dateTo: string,
  options?: {...}
): Promise<ProductMarginsReport>

export async function triggerRecalculation(
  dateFrom: string,
  dateTo: string
): Promise<{...}>
```

---

## 3) Cambios en Componentes

### MarginsDashboard.tsx
- Reemplaza `listProductMargins()` con `getProductMargins()` (Blueprint V2)
- Datos obtenidos directamente de snapshots de profit diarios
- Mapeador `mapProductMarginRow()` para convertir formato API
- Elimina tabs innecesarios (clientes/detalle) — solo productos
- Sigue mostrando: Top by profit, Worst by margin, Alerts

### PerdidasGanancias.tsx
- Reemplaza `useMovimientos()` hardcodeado con `getProfitReport()` 
- Obtiene datos de profit snapshots (últimos 30 días)
- Muestra: Total Sales, COGS, Gross Profit, Expenses, Net Profit, Net Margin %
- Error handling y loading states mejorados

### ImportadorExcelWithQueue.tsx
- Mantiene UI/UX idéntico
- Ahora envía archivos a `/documents/storage/upload` al subirlos
- Deduplicación automática por SHA256
- Los archivos quedan registrados en `document_files` y `document_versions`

---

## 4) Flujos de Datos

### Document Upload Flow
```
Usuario selecciona archivos
    ↓
handleFileChange/handleDrop()
    ↓
uploadDocument() → POST /documents/storage/upload
    ↓
document_files + document_versions (con SHA256)
    ↓
ImportQueueContext sigue procesando
```

### Profit Report Flow
```
PerdidasGanancias.tsx monta
    ↓
getProfitReport(dateFrom, dateTo)
    ↓
GET /reports/profit
    ↓
ProfitSnapshotDaily (aggregated)
    ↓
Renderiza: Sales, COGS, Expenses, Net Profit
```

### Product Margins Flow
```
MarginsDashboard.tsx monta
    ↓
getProductMargins(dateFrom, dateTo)
    ↓
GET /reports/product-margins
    ↓
ProductProfitSnapshot (grouped by product)
    ↓
Mapea respuesta, renderiza tabla
```

---

## 5) Archivos Modificados/Creados

### Nuevos:
- ✅ `apps/tenant/src/services/api/documents.ts`
- ✅ `apps/tenant/src/services/api/profit-reports.ts`

### Modificados:
- ✅ `apps/tenant/src/modules/importer/ImportadorExcelWithQueue.tsx`
- ✅ `apps/tenant/src/modules/reportes/MarginsDashboard.tsx`
- ✅ `apps/tenant/src/modules/accounting/components/PerdidasGanancias.tsx`

---

## 6) Próximos Pasos

1. **Testing**:
   ```bash
   npm test apps/tenant  # Validar componentes
   ```

2. **Validación en navegador**:
   - Subir archivos → Verificar en `/documents/storage`
   - Ver reportes → Verificar datos en snapshots
   - Verificar logs de eventos (event_outbox)

3. **Integración con Audit**:
   - Los uploads ya logean en `audit_log` (vía backend)
   - Los cambios en snapshots se pueden loguear en handlers

4. **Futuro**:
   - Agregar tab de "Detalles por Línea de Producto" usando `/reports/product-details` (si se implementa)
   - Dashboard de eventos en tiempo real (event_outbox consumer)
   - Exportar reportes a PDF/Excel

---

## Traducción i18n Requerida

Agregar a archivos de traducción:
```json
{
  "accounting.pl.totalSales": "Total Sales",
  "accounting.pl.cogs": "COGS",
  "accounting.pl.grossProfit": "Gross Profit",
  "accounting.pl.netMargin": "Net Margin",
  "accounting.pl.noData": "No data available"
}
```

---

**STATUS**: Frontend ahora usa 100% de las nuevas APIs Blueprint V2 ✅
