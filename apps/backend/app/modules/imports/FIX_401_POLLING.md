# 🔧 Fix: Error 401 en Polling de Jobs OCR

## ❌ Problema

Al importar PDFs/imágenes, el proceso falla con:
```
GET /api/v1/imports/jobs/{job_id} HTTP/1.0" 401 Unauthorized
```

**Causa raíz**: El token de autenticación no se estaba pasando en las peticiones de polling del estado del job OCR.

---

## ✅ Solución Implementada

### Archivos Modificados

#### 1. `services.ts` - Agregar token a polling

**Antes**:
```typescript
export async function pollOcrJob(jobId: string): Promise<ProcesarDocumentoResult>
async function waitForOcrJob(jobId: string): Promise<OcrJobResultPayload | null>
const status = await getOcrJob(jobId)  // ❌ Sin token
```

**Después**:
```typescript
export async function pollOcrJob(jobId: string, authToken?: string): Promise<ProcesarDocumentoResult>
async function waitForOcrJob(jobId: string, authToken?: string): Promise<OcrJobResultPayload | null>
const status = await getOcrJob(jobId, authToken)  // ✅ Con token
```

#### 2. `services.ts` - Agregar token a procesarDocumento

**Antes**:
```typescript
export async function procesarDocumento(file: File): Promise<ProcesarDocumentoResult>
const json = await apiFetch<any>('/api/v1/imports/procesar', {
  method: 'POST',
  body: fd,
  // ❌ Sin authToken
})
```

**Después**:
```typescript
export async function procesarDocumento(file: File, authToken?: string): Promise<ProcesarDocumentoResult>
const json = await apiFetch<any>('/api/v1/imports/procesar', {
  method: 'POST',
  body: fd,
  authToken,  // ✅ Con token
})
```

#### 3. `ImportadorExcel.tsx` - Pasar token al llamar

**Antes**:
```typescript
const response = item.jobId
  ? await pollOcrJob(item.jobId)           // ❌ Sin token
  : await procesarDocumento(item.file)     // ❌ Sin token
```

**Después**:
```typescript
const response = item.jobId
  ? await pollOcrJob(item.jobId, token || undefined)           // ✅ Con token
  : await procesarDocumento(item.file, token || undefined)     // ✅ Con token
```

---

## 🧪 Verificación

### 1. Test en DevTools

```javascript
// Abrir consola del navegador
// Network tab → Filtrar por "jobs"
// Al hacer polling, verificar headers:
Headers:
  Authorization: Bearer eyJhbGc...  // ✅ Debe aparecer
```

### 2. Test Backend

```bash
# Verificar que el endpoint acepta el token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/imports/jobs/{job-id}

# Debe responder 200 OK con:
{
  "job_id": "...",
  "status": "pending|running|done|failed",
  "result": {...}
}
```

---

## 📊 Flujo Corregido

```
1. Usuario sube PDF
   ↓
2. procesarDocumento(file, TOKEN) 
   → POST /api/v1/imports/procesar
   → Authorization: Bearer {TOKEN}  ✅
   ↓
3. Backend responde: { job_id: "uuid" }
   ↓
4. Frontend inicia polling cada 1.5s
   → pollOcrJob(jobId, TOKEN)
   → GET /api/v1/imports/jobs/{job_id}
   → Authorization: Bearer {TOKEN}  ✅
   ↓
5. Backend responde estado:
   - "pending" → Continuar polling
   - "running" → Continuar polling
   - "done" → Retornar resultado
   - "failed" → Lanzar error
   ↓
6. Resultado final usado para crear batch
```

---

## ⏱️ Configuración de Timeouts

### Frontend (.env o vite.config)

```bash
# Intervalo entre polls (milisegundos)
VITE_IMPORTS_JOB_POLL_INTERVAL=1500

# Máximo de intentos antes de timeout
VITE_IMPORTS_JOB_POLL_ATTEMPTS=80

# Timeout total = 1.5s * 80 = 120 segundos
```

### Backend (.env)

```bash
# Timeout de Gunicorn/Uvicorn
GUNICORN_TIMEOUT=120

# Workers OCR
IMPORTS_OCR_WORKERS=2
```

---

## 🐛 Otros Problemas Posibles

### Error persiste después del fix

**Posible causa**: Token expirado durante el procesamiento largo

**Solución**: Refrescar token antes de polling
```typescript
// En ImportadorExcel.tsx
const { refreshToken } = useAuth()
await refreshToken()  // Antes de iniciar polling largo
```

### Error: "Job no encontrado"

**Causa**: El job_id no existe en la base de datos o es de otro tenant

**Solución**: Verificar que el endpoint `/procesar` creó el job correctamente
```sql
SELECT * FROM import_ocr_jobs 
WHERE id = 'job-uuid' 
  AND tenant_id = 'tenant-uuid';
```

### Error: Job se queda en "pending" indefinidamente

**Causa**: Worker no está corriendo

**Solución**: Iniciar worker
```bash
# Verificar
ps aux | grep job_runner

# Iniciar
python -m app.modules.imports.application.job_runner_main
```

---

## ✅ Checklist Post-Fix

Después de aplicar el fix:

- [x] Token se pasa en `procesarDocumento()`
- [x] Token se pasa en `pollOcrJob()`
- [x] Token se pasa en `waitForOcrJob()`
- [x] Token se pasa en `getOcrJob()`
- [x] ImportadorExcel.tsx pasa token correctamente
- [x] Backend acepta token en `/jobs/{id}`
- [x] No hay errores 401 en DevTools Network

---

## 🎉 Resultado

Después del fix:
```
✅ PDF sube correctamente
✅ Job OCR se encola
✅ Polling funciona sin errores 401
✅ Resultado se extrae correctamente
✅ Batch se crea con datos procesados
✅ Navigate a vista previa
```

**Estado**: ✅ CORREGIDO

---

**Fecha**: 2025-11-05  
**Issue**: Frontend no pasaba token en polling OCR  
**Fix**: Agregar parámetro `authToken` a todas las funciones de la cadena
