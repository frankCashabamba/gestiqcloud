# ⚡ Quick Start: Ollama + OVHCloud AI Setup

**5 minutos para tener IA funcionando**

---

## 🚀 OPCIÓN A: Desarrollo (Ollama Local) - 5 MIN

### 1️⃣ Instalar Ollama

**macOS/Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
- Descargar desde: https://ollama.ai/download
- Ejecutar instalador

### 2️⃣ Descargar Modelo

```bash
ollama pull llama3.1:8b
```

### 3️⃣ Iniciar Ollama

```bash
ollama serve
```

Debería ver:
```
2025/02/16 10:30:00 Listening on 127.0.0.1:11434
```

### 4️⃣ Configurar Backend

En `.env`:
```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
IMPORT_AI_CACHE_ENABLED=true
```

### 5️⃣ Iniciar Backend

```bash
cd apps/backend
uvicorn main:app --reload
```

### ✅ Test

```bash
curl -X POST http://localhost:8000/api/v1/imports/uploads/analyze \
  -F "file=@factura.xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🌐 OPCIÓN B: Producción (OVHCloud) - 10 MIN

### 1️⃣ Obtener Credenciales OVHCloud

1. Ir a: https://manager.eu.ovhcloud.com/
2. Login → **Settings** → **API**
3. Crear aplicación:
   - Name: `gestiqcloud-ai`
   - Descargar credenciales

### 2️⃣ Guardar Credenciales

En `.env.production`:
```bash
AI_PROVIDER=ovhcloud
OVHCLOUD_API_KEY=your-key-here
OVHCLOUD_API_SECRET=your-secret-here
OVHCLOUD_BASE_URL=https://manager.eu.ovhcloud.com/api/v2
OVHCLOUD_MODEL=gpt-4o
IMPORT_AI_CACHE_ENABLED=true
IMPORT_AI_CACHE_TTL=604800
```

### 3️⃣ Validar Credenciales

```bash
curl -X GET \
  "https://manager.eu.ovhcloud.com/api/v2/ai/health" \
  -H "Authorization: Bearer $OVHCLOUD_API_KEY" \
  -H "X-OVH-Secret: $OVHCLOUD_API_SECRET"

# Debería retornar: { "status": "operational", ... }
```

### 4️⃣ Desplegar en Producción

```bash
# En servidor de producción
export AI_PROVIDER=ovhcloud
export OVHCLOUD_API_KEY=your-key
export OVHCLOUD_API_SECRET=your-secret

# Reiniciar backend
systemctl restart gestiqcloud-backend
```

### 5️⃣ Verificar

```bash
curl http://your-production-domain:8000/api/v1/imports/ai/health
```

---

## 📊 Comparativa Rápida

| | Ollama | OVHCloud |
|---|--------|----------|
| **Costo** | $0 | $0.005-0.015/req |
| **Precisión** | 85% | 95%+ |
| **Setup** | 5 min | 10 min |
| **Internet** | No | Sí |
| **Ideal para** | Desarrollo | Producción |

---

## 🐛 Troubleshooting Rápido

### Ollama no funciona

```bash
# Verificar que está corriendo
curl http://localhost:11434/api/tags

# Reintentar
ollama serve
```

### OVHCloud da error

```bash
# Verificar credenciales
echo "API_KEY: $OVHCLOUD_API_KEY"
echo "API_SECRET: $OVHCLOUD_API_SECRET"

# Validar conexión
curl -v https://manager.eu.ovhcloud.com/api/v2/ai/health
```

### Backend no ve provider

```bash
# Logs del backend
tail -f logs/backend.log | grep -i "ai\|provider"

# Verificar .env
cat .env | grep -i "AI_PROVIDER\|OLLAMA\|OVHCLOUD"
```

---

## 📚 Documentación Completa

- **Detallado:** `SETUP_OLLAMA_OVHCLOUD.md`
- **Review:** `REVISION_IA_IDENTIFICACION_DOCUMENTOS.md`
- **Script automático:** `setup_ai_providers.sh`

---

## 💡 Próximos Pasos

### Una vez funcionando:

1. **Test de clasificación:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/imports/uploads/analyze \
     -F "file=@test.xlsx"
   ```

2. **Ver metrics:**
   ```bash
   curl http://localhost:8000/api/v1/imports/ai/telemetry
   ```

3. **Usar en frontend:**
   - Subir archivo en el importador
   - Sistema lo clasifica automáticamente
   - Confirmar o ajustar mapping
   - ¡Listo!

---

## 🎯 Resumen

**Desarrollo:** Solo instalar Ollama y cambiar .env
**Producción:** Obtener credenciales OVHCloud y configurar
**Total:** 15 minutos para ambos entornos operativos

**Status:** ✅ Listo para usar
