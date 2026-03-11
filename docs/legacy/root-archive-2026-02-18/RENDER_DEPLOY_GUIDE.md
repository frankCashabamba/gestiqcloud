# 🚀 DEPLOY GUIDE: GESTIQCLOUD EN RENDER

**Para: SPRINT 5 (Semana 9)**
**Tiempo:** 2-3 horas
**Costo:** FREE tier (PostgreSQL 256MB, Redis 30GB gratis)

---

## 📋 CHECKLIST PRE-DEPLOY

```
ANTES DE EMPEZAR:
  ☐ Cuenta en render.com creada
  ☐ GitHub account conectado
  ☐ Código limpio (SPRINT 0 completado)
  ☐ Tests pasando 100%
  ☐ .env.render.example completado
  ☐ Variables sensibles generadas (secrets)
```

---

## 🏗️ PASO 1: CREAR POSTGRESQL EN RENDER

### **1.1 Nueva base de datos**

```
1. Ir a: render.com/dashboard
2. Click: "New +" → "PostgreSQL"
3. Llenar formulario:
   - Name:              gestiqcloud-db
   - Database:          gestiqcloud
   - User:              gestiqcloud_user
   - Region:            Frankfurt (más cerca de Europa)
   - Version:           14 (o 15)
   - Instance Type:     Free

4. Click: "Create Database"
   → Esperar 2-3 minutos
   → Copiar CONNECTION STRING (ejemplo):
      postgresql://user:password@dpg-xxx.render.com:5432/gestiqcloud
```

### **1.2 Nota importante**

```
⚠️ Free tier Render:
- 256 MB storage
- Sleep después 15 min inactividad
- Suficiente para MVP/testing

Para producción:
- Upgrade a "Starter" (~$7/mes)
- 100 GB storage
- No duerme
```

---

## 💾 PASO 2: CREAR REDIS EN RENDER

### **2.1 Nueva instancia Redis**

```
1. Dashboard → "New +" → "Redis"
2. Llenar:
   - Name:              gestiqcloud-redis
   - Region:            Frankfurt
   - Version:           7
   - Instance Type:     Free

3. Click: "Create Redis"
   → Copiar CONNECTION STRING:
      redis://:password@redis-xxx.render.com:6379
```

---

## 🔧 PASO 3: DEPLOY BACKEND (FastAPI)

### **3.1 Nueva Web Service**

```
1. Dashboard → "New +" → "Web Service"
2. Conectar GitHub:
   - "Connect account" si primera vez
   - Select repo: gestiqcloud
   - Branch: main (o develop)

3. Configurar:
   - Name:                   gestiqcloud-api
   - Runtime:                Python 3
   - Build command:          pip install -r apps/backend/requirements.txt
   - Start command:          cd apps/backend && gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
   - Instance Type:          Free
   - Region:                 Frankfurt
```

### **3.2 Environment Variables**

```
1. Settings → "Environment"
2. Agregar variables (copiar de .env.render.example):

   # Database (auto-inyectada si linkeas DB)
   DATABASE_URL=postgresql://...  (Copiar de PostgreSQL)

   # Cache
   REDIS_URL=redis://...          (Copiar de Redis)

   # Security
   SECRET_KEY=                     (Generar con: python -c "import secrets; print(secrets.token_urlsafe(32))")
   JWT_SECRET_KEY=                 (Generar igual)
   JWT_ALGORITHM=HS256

   # CORS
   CORS_ORIGINS=https://gestiqcloud-admin.onrender.com,https://gestiqcloud-tenant.onrender.com

   # Email (si usas SendGrid)
   SENDGRID_API_KEY=               (Tu API key)
   SMTP_FROM_EMAIL=noreply@gestiqcloud.com

   # Others
   ENV=production
   DEBUG=false
```

### **3.3 Link Database & Redis**

```
1. Settings → "Databases"
2. Click: "Link Database"
   - Select: gestiqcloud-db
   → Auto-inyecta DATABASE_URL

3. Click: "Link Redis"
   - Select: gestiqcloud-redis
   → Auto-inyecta REDIS_URL
```

### **3.4 Deploy script**

```
Si necesita migrations:

Settings → "Build & Deploy"
→ Post-deploy command:
   python ops/scripts/migrate_all_migrations_idempotent.py
```

### **3.5 Deploy!**

```
Click: "Deploy"
→ Esperar 5-10 minutos
→ Ver logs en "Logs"

✓ Esperado:
  "Application startup complete"
  "Uvicorn running on 0.0.0.0:8000"

✗ Si falla:
  Ver logs → buscar error
  Común: DATABASE_URL missing
```

### **3.6 Probar backend**

```bash
# Obtener URL del servicio
https://gestiqcloud-api.onrender.com

# Probar health
curl https://gestiqcloud-api.onrender.com/health
# Response: {"status":"ok"}

# Ver Swagger docs
https://gestiqcloud-api.onrender.com/docs
```

---

## 🎨 PASO 4: DEPLOY ADMIN (React)

### **4.1 Nueva Static Site**

```
1. Dashboard → "New +" → "Static Site"
2. Conectar GitHub:
   - Repo: gestiqcloud
   - Branch: main

3. Configurar:
   - Name:                   gestiqcloud-admin
   - Build command:          cd apps/admin && npm install && npm run build
   - Publish directory:      apps/admin/dist
   - Instance Type:          Free
   - Region:                 Frankfurt
```

### **4.2 Environment Variables**

```
Settings → "Environment"

Add:
  VITE_API_URL=https://gestiqcloud-api.onrender.com/api
  VITE_BASE_PATH=/
  VITE_ADMIN_ORIGIN=https://gestiqcloud-admin.onrender.com
  VITE_TENANT_ORIGIN=https://gestiqcloud-tenant.onrender.com
```

### **4.3 Deploy**

```
Click: "Deploy"
→ Esperar 3-5 minutos

✓ Esperado:
  "Build successful"
  "Live at https://gestiqcloud-admin.onrender.com"
```

### **4.4 Probar**

```
https://gestiqcloud-admin.onrender.com
→ Debe cargar login page
→ Intentar login con credenciales de test
```

---

## 👥 PASO 5: DEPLOY TENANT (React PWA)

### **5.1 Nueva Static Site**

```
1. Dashboard → "New +" → "Static Site"
2. GitHub:
   - Repo: gestiqcloud
   - Branch: main

3. Configurar:
   - Name:                   gestiqcloud-tenant
   - Build command:          cd apps/tenant && npm install && npm run build
   - Publish directory:      apps/tenant/dist
   - Instance Type:          Free
   - Region:                 Frankfurt
```

### **5.2 Environment Variables**

```
Settings → "Environment"

Add:
  VITE_API_URL=https://gestiqcloud-api.onrender.com/api
  VITE_BASE_PATH=/
  VITE_ADMIN_ORIGIN=https://gestiqcloud-admin.onrender.com
  VITE_TENANT_ORIGIN=https://gestiqcloud-tenant.onrender.com
```

### **5.3 Deploy**

```
Click: "Deploy"
→ Esperar 3-5 minutos
→ Live at https://gestiqcloud-tenant.onrender.com
```

---

## ✅ PASO 6: VALIDACIÓN POST-DEPLOY

### **6.1 Health checks**

```bash
# Backend health
curl -s https://gestiqcloud-api.onrender.com/health | jq .

# Backend ready
curl -s https://gestiqcloud-api.onrender.com/ready | jq .

# Ambos deben retornar:
{
  "status": "ok",
  ...
}
```

### **6.2 Frontend load**

```
Browser:
  https://gestiqcloud-admin.onrender.com
  → Debe cargar sin errors
  → DevTools → Network: no red errors
  → DevTools → Console: no JS errors

  https://gestiqcloud-tenant.onrender.com
  → Mismo
```

### **6.3 Database test**

```bash
# Login backend para verificar DB
curl -X POST https://gestiqcloud-api.onrender.com/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identificador":"ADMIN","password":"secret"}'

# Esperado: 200 OK + access_token
# Si error: DATABASE_URL problem
```

### **6.4 Email test**

```bash
# Si SendGrid configurado:
curl -X POST https://gestiqcloud-api.onrender.com/api/v1/settings/test-email \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com"}'
```

---

## 🔄 PASO 7: SETUP AUTO-DEPLOY

### **7.1 Deploy automático en cada push**

```
Render auto-deploya cuando pusheas a main branch

Para disable:
  - Settings → "Auto-deploy" → Off
  - Deploy manualmente con "Deploy" button
```

### **7.2 Monitorear deploys**

```
Dashboard → "Events"
Ver todos los deploys anteriores y estado
```

---

## 🚨 TROUBLESHOOTING

### **Backend no arranca**

```
Problema: "Application failed to start"

Soluciones:
1. Ver logs: Dashboard → Backend → "Logs"
2. Buscar error específico
3. Común: DATABASE_URL missing
   → Verificar PostgreSQL linked
   → Restart service

4. Común: Import error
   → Verificar requirements.txt actualizado
   → pip install -r apps/backend/requirements.txt

5. Common: SQL migration runner fails
   → Ver logs del post-deploy command
   → Manual fix en Render shell (si acceso)
```

### **Frontend no carga**

```
Problema: Blank page, 404, CORS errors

Soluciones:
1. CORS error:
   → Backend CORS_ORIGINS includes admin/tenant URLs
   → Check: https://api.render.com/health (no CORS needed)

2. API_URL wrong:
   → Check VITE_API_URL environment var
   → Must match backend URL

3. Service Worker cached:
   → Browser: DevTools → Application → Service Workers
   → Unregister all
   → Hard refresh (Ctrl+Shift+R)
```

### **Database sleep (free tier)**

```
Problema: Timeouts cuando free DB duerme

Soluciones:
1. No hay solución en free tier
2. Upgrade a Starter (~$7/mes)
3. O: Hacer keep-alive curl cada 15 min
   (Render cron o external service)
```

### **Redis timeout**

```
Mismo que DB, upgrade para fix
```

---

## 📊 MONITOREO POST-GO-LIVE

### **7.1 Logs**

```
Render Dashboard:
  - Backend → "Logs"
  - Admin → "Logs"
  - Tenant → "Logs"

Buscar:
  - Errores 5xx
  - OOM (Out of Memory)
  - Database connection errors
  - Auth failures
```

### **7.2 Performance**

```
Render Dashboard:
  - Backend → "Metrics"
  - Ver: CPU, Memory, Disk

Alertas:
  - Si Memory > 90%: upgrade
  - Si Disk > 90%: cleanup logs o upgrade
```

### **7.3 Backup**

```
PostgreSQL:
  - Render auto-backups daily
  - Retention: 7 días free, 30 días paid
  - Manual: Render Dashboard → Database → "Backups"

Redis:
  - No auto-backup en free tier
  - Implement redis.save() periodic si importante
```

---

## 🎯 URLS FINALES

```
Admin:   https://gestiqcloud-admin.onrender.com
Tenant:  https://gestiqcloud-tenant.onrender.com
API:     https://gestiqcloud-api.onrender.com

Healthcheck:
  https://gestiqcloud-api.onrender.com/health
  https://gestiqcloud-api.onrender.com/ready

Docs:
  https://gestiqcloud-api.onrender.com/docs        (Swagger)
  https://gestiqcloud-api.onrender.com/redoc       (ReDoc)
```

---

## 💰 COSTOS ESTIMADOS (RENDER)

```
FREE TIER:
  Backend:   $0 (5000 hrs/mes)
  Admin:     $0 (100 GB/mes bandwidth)
  Tenant:    $0 (100 GB/mes bandwidth)
  Database:  $0 (256 MB, 1 project)
  Redis:     $0 (30 GB, 1 project)
  TOTAL:     $0/mes ✅

STARTER TIER (si escalas):
  Backend:   $7/mes (CPU + Memory garantizado)
  Database:  $7/mes (1 GB storage)
  TOTAL:     ~$15/mes

PRO TIER:
  Backend:   $20/mes
  Database:  $29/mes
  TOTAL:     ~$50/mes
```

---

## ✅ POST-DEPLOY CHECKLIST

```
DAY 1:
  ☐ Health checks passing
  ☐ Frontend loads
  ☐ Login works
  ☐ POS funciona
  ☐ Facturación OK
  ☐ Stock movements OK

DAY 2-7:
  ☐ Monitor logs daily
  ☐ Test all Tier 1 workflows
  ☐ Backup data (manual)
  ☐ Document any issues
  ☐ Update README con URLs

WEEK 2:
  ☐ Security audit Render setup
  ☐ Performance optimization
  ☐ Setup monitoring alertas
  ☐ Data retention policy
  ☐ Backup automation

WEEK 4:
  ☐ Upgrade to Starter si needed
  ☐ Setup custom domain (opcional)
  ☐ Email delivery verification
  ☐ SII testing (si aplica España)
```

---

**Siguiente:** SPRINT 5 Week 9 → Deploy a Render
**Si necesitas help:** Check logs en Render Dashboard
