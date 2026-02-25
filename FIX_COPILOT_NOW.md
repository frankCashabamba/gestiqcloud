# 🚀 FIX - Copilot + IA (Paso a Paso)

## ¿Por qué no funciona?

El **código está escrito** pero:
1. ❌ Frontend sin recompilación
2. ❌ Backend probablemente sin restart
3. ❌ Caché del navegador

**Solución: 5 minutos de trabajo**

---

## PASO 1: Detener todo (2 min)

### En Terminal 1 (Frontend):
```bash
# Si está corriendo, presiona:
CTRL + C

# Luego:
cd c:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud\apps\tenant
```

### En Terminal 2 (Backend):
```bash
# Si está corriendo, presiona:
CTRL + C

# Luego:
cd c:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud\apps\backend
```

---

## PASO 2: Recompila Frontend (1 min)

En Terminal 1 (Tenant):
```bash
npm run build
```

**Espera a que termine.** Debería ver:
```
✓ 1234 modules transformed

dist/index.html                0.45 kB │ gzip:  0.27 kB
dist/assets/index-abc.js    234.56 kB │ gzip: 45.23 kB
```

---

## PASO 3: Inicia Frontend (30 seg)

Sigue en Terminal 1:
```bash
npm run dev
```

**Espera a que diga:**
```
  VITE v5.x.x  ready in 245 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

---

## PASO 4: Inicia Backend (1 min)

En Terminal 2:
```bash
python -m uvicorn app.main:app --reload
```

**Espera a que diga:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

## PASO 5: Limpia caché del navegador (30 seg)

En el navegador:
1. Abre DevTools: **F12**
2. Click derecho en botón "Actualizar"
3. Selecciona **"Vaciar caché e recargar"**

O manualmente:
```javascript
// En consola de DevTools (F12):
localStorage.clear()
sessionStorage.clear()
location.reload()
```

---

## PASO 6: Abre Dashboard

En el navegador:
```
http://localhost:8082/kusi-panaderia/copilot
```

**Debería ver:**
- ✅ Datos cargados (no vacíos)
- ✅ Botón "💡 Insights" en cada card
- ✅ 3 tarjetas de sugerencias arriba

---

## ✅ Checklist Final

Antes de considerar "listo", verifica:

- [ ] Frontend compiló sin errores
- [ ] Backend iniciado correctamente
- [ ] Navegador sin errores en F12 Console
- [ ] Dashboard muestra datos (no vacíos)
- [ ] Botón "Actualizar" funciona
- [ ] Hay sugerencias en la parte superior

---

## 🔍 Si aún no funciona:

### 1. Abre DevTools (F12)
Pestaña **Console** - ¿hay errores en rojo?
- Si dice **404** en `/ai/ask` → Backend no actualizado
- Si dice **CORS** → Revisar CORS_ORIGINS en .env
- Si dice **TypeError** → Error en código frontend

### 2. Network Tab (F12)
- Haz click en "Actualizar"
- Busca request a `/api/v1/tenant/ai/ask`
- ¿Retorna datos o error?

### 3. Verifica Backend logs
En Terminal 2, ¿ves mensaje como:
```
INFO:     POST /api/v1/tenant/ai/ask
```
Si no, el endpoint no está siendo llamado.

---

## 💡 Pro Tips

### Para forzar rebuild sin caché:
```bash
cd apps/tenant
npm run build -- --force
npm run dev -- --force
```

### Para ver logs detallados:
```bash
# Backend
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload

# Frontend - busca errores en Network
F12 → Network → verifica response JSON
```

### Para resetear todo (nuclear option):
```bash
cd apps/tenant
rm -rf node_modules dist
npm install
npm run build
npm run dev

# Y en otra terminal:
cd apps/backend
python -m pip install --upgrade -r requirements.txt
python -m uvicorn app.main:app --reload
```

---

## 📸 Resultado Esperado

**Antes:**
```
[Dashboard vacío con [] en datos]
```

**Después:**
```
🔴 Stock    │ 🟡 Ventas   │ 🟢 Finance
5 productos │ Oportunidad │ Revisar cobros
────────────────────────────────────
Ventas por Mes [💡 Insights]
[Datos reales + Hallazgos de IA]
────────────────────────────────────
🤖 Modelo IA: llama3.1:8b
⏱️ Sugerencias generadas: 21/02/2025 12:30
```

---

## ⏱️ Tiempo Total: 5-10 minutos

1. Detener servicios: 2 min
2. Recompilar frontend: 1 min
3. Iniciar servicios: 2 min
4. Limpiar caché navegador: 1 min
5. Verificar: 1-2 min

**Si todo está bien:** ✅ Done

**Si hay error:** Comparte output de:
- DevTools Console (F12)
- Backend logs (Terminal 2)
- Response de Network tab
