# 🔧 Debug: Copilot + IA No Funciona

## El Dashboard se ve así:
```
❌ Pedidos por mes: []
❌ Top productos: (vacío)
❌ Cobros/Pagos: []
✅ Stock bajo: (muestra datos, pero formato extraño)
```

---

## 🔍 Checklist de Debug

### 1. **Frontend compilado correctamente**
- [ ] ¿Ejecutaste `npm run build`?
- [ ] ¿Reinicias el servidor frontend después?

```bash
cd apps/tenant
npm run build
npm run dev
```

### 2. **Backend corriendo con cambios**
- [ ] ¿El backend se reinició después de cambios?
- [ ] ¿Está en puerto 8000?

```bash
cd apps/backend
python -m uvicorn app.main:app --reload
# Debería mostrar:
# INFO:     Application startup complete
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. **Abre Consola del Navegador**
Presiona `F12` y revisa:

```javascript
// Debería haber errores como:
// - CORS error (si frontend y backend no están en mismo origen)
// - 404 on /api/v1/tenant/ai/ask
// - 401 Unauthorized (token inválido)
// - TypeError (problema en código)
```

### 4. **Test endpoint manualmente**

**PowerShell (Windows):**
```powershell
$token = "your-jwt-token"
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    topic = "ventas_mes"
    with_ai_insights = $true
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/tenant/ai/ask" `
    -Method POST `
    -Headers $headers `
    -Body $body | ConvertTo-Json
```

**Bash (macOS/Linux):**
```bash
curl -X POST http://localhost:8000/api/v1/tenant/ai/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "ventas_mes", "with_ai_insights": true}' \
  | jq .
```

### 5. **Verifica IA disponible**

```bash
# Test si Ollama está corriendo
curl http://localhost:11434/api/tags | jq .

# Si no:
ollama pull llama3.1:8b
ollama serve
```

---

## 📋 Errores Comunes

### Error: "Module not found: app.modules.copilot.services"
**Causa:** Python no encuentra el módulo
**Solución:**
```bash
cd apps/backend
# Asegúrate que estés en venv
python -c "from app.modules.copilot.services import query_readonly_enhanced; print('✅ OK')"
```

### Error: "CORS policy: No 'Access-Control-Allow-Origin'"
**Causa:** Frontend en 8082 pero backend en 8000
**Solución:** Verifica CORS_ORIGINS en .env
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:8081,http://localhost:8082
```

### Error: "ai_insights is undefined"
**Causa:** Frontend antiguo que no sabe de ai_insights
**Solución:**
```bash
cd apps/tenant
# Fuerza rebuild
rm -rf node_modules dist
npm install
npm run build
npm run dev
```

### Error: "No hay proveedores IA disponibles"
**Causa:** Ollama no está corriendo
**Solución:**
```bash
# Terminal 1: Inicia Ollama
ollama serve

# Terminal 2: Prueba conexión
curl http://localhost:11434/api/status
```

### Error: "Request body error: ai_insights is not valid"
**Causa:** El modelo de respuesta no espera ai_insights
**Solución:** Limpia caché y regenera tipos:
```bash
cd apps/backend
python -m mypy app/modules/copilot/
```

---

## 🧪 Test Step-by-Step

### Test 1: ¿Funciona endpoint básico?
```bash
curl -X POST http://localhost:8000/api/v1/tenant/ai/ask \
  -H "Authorization: Bearer dummy" \
  -H "Content-Type: application/json" \
  -d '{"topic": "ventas_mes"}'
```

**Esperado:**
```json
{
  "cards": [{"title": "...", "series": [...]}],
  "sql": "SELECT ...",
  "note": "..."
}
```

### Test 2: ¿Devuelve ai_insights?
Mismo curl pero con `"with_ai_insights": true`

**Esperado:**
```json
{
  "cards": [...],
  "ai_insights": {
    "findings": [...],
    "trends": [...],
    "recommendations": [...]
  },
  "ai_model": "llama3.1:8b"
}
```

### Test 3: ¿Funciona /ai/suggestions?
```bash
curl -X GET http://localhost:8000/api/v1/tenant/ai/suggestions \
  -H "Authorization: Bearer dummy"
```

**Esperado:**
```json
{
  "suggestions": [
    {
      "type": "inventory",
      "priority": "high",
      "content": "...",
      "action": "..."
    }
  ],
  "generated_at": "2025-02-21T...",
  "ai_enabled": true
}
```

---

## 📊 Verificar Datos en BD

Si los endpoints retornan datos vacíos, el problema es la BD:

```sql
-- Conecta a la BD
psql postgresql://user:password@localhost:5432/gestiqcloud

-- Verifica si hay datos
SELECT COUNT(*) FROM sales_orders;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM stock_items;

-- Si retorna 0, inserta datos de prueba
INSERT INTO sales_orders (customer_id, status, created_at)
VALUES (1, 'draft', now());
```

---

## 🚨 Último Resort: Logs Detallados

```bash
# Terminal backend con debug
cd apps/backend
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload

# Frontend con modo verbose
cd apps/tenant
npm run dev -- --debug
```

**Busca en logs:**
- `IA query (analysis)`
- `AI response`
- `Error in query_readonly_enhanced`
- `Available provider`

---

## ✅ Verificar Que Todo Funciona

```bash
# 1. Backend iniciado
echo "1. Backend running?"
curl -s http://localhost:8000/health | jq . && echo "✅" || echo "❌"

# 2. Ollama disponible
echo "2. Ollama available?"
curl -s http://localhost:11434/api/tags | jq . && echo "✅" || echo "❌"

# 3. DB conectada
echo "3. Database connected?"
psql postgresql://user:password@localhost:5432/gestiqcloud -c "SELECT 1" && echo "✅" || echo "❌"

# 4. Endpoint básico
echo "4. /ai/ask endpoint?"
curl -s -X POST http://localhost:8000/api/v1/tenant/ai/ask \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{"topic": "ventas_mes"}' | jq . && echo "✅" || echo "❌"
```

---

## 💡 Próximos Pasos

1. **Abre DevTools** (F12)
2. **Ve a Network** tab
3. **Haz click en "Actualizar"**
4. **Busca request a** `/api/v1/tenant/ai/ask`
5. **Revisa response** - ¿tiene ai_insights?
6. **Si error** - pega el error aquí

**Status de debug:** Esperando output de consola
