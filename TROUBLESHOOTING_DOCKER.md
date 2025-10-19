# 🔧 Guía de Troubleshooting - Docker en Windows

## ❌ Error Actual

```
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/...": 
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**Causa**: Docker Desktop no está ejecutándose en Windows.

---

## ✅ Solución Paso a Paso

### 1️⃣ Iniciar Docker Desktop

**Opción A - Interfaz Gráfica:**
```
1. Buscar "Docker Desktop" en el menú inicio de Windows
2. Click derecho → Ejecutar como administrador (primera vez)
3. Esperar a que aparezca el ícono de Docker en la bandeja del sistema
4. El ícono debe estar verde/animado (significa que está corriendo)
```

**Opción B - PowerShell:**
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

**Verificar que Docker está corriendo:**
```powershell
docker ps
# Debe mostrar una tabla (aunque esté vacía)
```

---

### 2️⃣ Verificar Variables de Entorno

El error también menciona variables faltantes. Crear archivo `.env` en la raíz:

```powershell
# Crear .env en la raíz del proyecto
New-Item -Path ".env" -ItemType File -Force
```

**Contenido del .env:**
```env
# Base de datos
DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root
POSTGRES_DB=gestiqclouddb_dev

# Backend
PYTHONPATH=/app:/apps
IMPORTS_ENABLED=1
FRONTEND_URL=http://localhost:8081

# Feature Flags
ELECTRIC_SYNC_ENABLED=0
IMPORTS_VALIDATE_CURRENCY=true
IMPORTS_REQUIRE_CATEGORIES=true

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Pagos (opcional para testing)
STRIPE_SECRET_KEY=sk_test_...
KUSHKI_MERCHANT_ID=...
PAYPHONE_TOKEN=...
```

---

### 3️⃣ Opción 1: Docker Compose Completo

```powershell
# Levantar todos los servicios
docker compose up -d --build

# Ver logs
docker compose logs -f

# Ver estado
docker compose ps
```

**Servicios que se levantan:**
- ✅ `db` - PostgreSQL 15 (puerto 5432)
- ✅ `migrations` - Aplicar migraciones SQL
- ✅ `backend` - FastAPI (puerto 8000)
- ✅ `admin` - PWA Admin (puerto 8081)
- ✅ `tenant` - PWA Tenant (puerto 5173)
- ✅ `redis` - Redis para Celery (puerto 6379)
- ✅ `celery-worker` - Workers de e-factura

---

### 4️⃣ Opción 2: Solo DB + Backend Local (Desarrollo)

Si prefieres correr backend en local con hot-reload:

```powershell
# 1. Solo DB + Redis
docker compose up -d db redis

# 2. Aplicar migraciones manualmente
python scripts/py/bootstrap_imports.py --dir ops/migrations

# 3. Backend local con uvicorn
cd apps/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend local (otra terminal)
cd apps/tenant
npm install
npm run dev
```

---

### 5️⃣ Verificar que Todo Funciona

```powershell
# Health check backend
curl http://localhost:8000/health

# Health check POS
curl http://localhost:8000/api/v1/pos/registers

# Frontend
# Abrir navegador: http://localhost:8081
```

---

## 🐛 Errores Comunes

### Error: "Cannot connect to Docker daemon"
**Solución**: Docker Desktop no está corriendo. Ver paso 1️⃣

### Error: "Port 5432 already in use"
**Causa**: Ya tienes PostgreSQL instalado localmente.

**Solución A - Cambiar puerto:**
```yaml
# En docker-compose.yml
services:
  db:
    ports:
      - "5433:5432"  # Cambiar de 5432 a 5433
```

**Solución B - Detener PostgreSQL local:**
```powershell
# Detener servicio PostgreSQL de Windows
Stop-Service postgresql-x64-15
```

### Error: "network proyecto_default not found"
```powershell
# Recrear red de Docker
docker compose down
docker compose up -d
```

### Error: "Unable to build image"
```powershell
# Limpiar caché de Docker
docker system prune -a --volumes

# Rebuild forzado
docker compose build --no-cache
docker compose up -d
```

---

## 📋 Comandos Útiles

### Gestión de Contenedores
```powershell
# Listar contenedores corriendo
docker ps

# Listar todos (incluidos detenidos)
docker ps -a

# Detener todos
docker compose down

# Detener y eliminar volúmenes
docker compose down -v

# Ver logs de un servicio
docker compose logs backend -f

# Entrar a un contenedor
docker exec -it backend bash
docker exec -it db psql -U postgres -d gestiqclouddb_dev
```

### Estado del Sistema
```powershell
# Ver imágenes
docker images

# Ver uso de disco
docker system df

# Ver redes
docker network ls
```

### Limpieza
```powershell
# Limpiar contenedores detenidos
docker container prune

# Limpiar imágenes sin usar
docker image prune -a

# Limpiar todo (¡cuidado!)
docker system prune -a --volumes
```

---

## 🔍 Debug Avanzado

### Ver Variables de Entorno en Contenedor
```powershell
docker exec backend env | grep DB_DSN
docker exec backend env | grep IMPORTS_ENABLED
```

### Verificar Logs de Migraciones
```powershell
docker compose logs migrations
```

### Conectarse a PostgreSQL
```powershell
# Desde host (si puerto expuesto)
psql -h localhost -U postgres -d gestiqclouddb_dev

# Desde contenedor
docker exec -it db psql -U postgres -d gestiqclouddb_dev

# Ver tablas
\dt

# Ver tenants
SELECT * FROM tenants;
```

### Test de Conectividad
```powershell
# Ping a DB desde backend
docker exec backend ping db

# Test conexión DB
docker exec backend python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:root@db:5432/gestiqclouddb_dev'); print('OK')"
```

---

## 🚀 Setup Rápido (Una Línea)

**Si Docker Desktop está corriendo:**

```powershell
docker compose down -v && docker compose up -d --build && timeout /t 30 && docker compose logs migrations && curl http://localhost:8000/health
```

---

## 📊 Checklist Final

Antes de probar el POS, verificar:

- [ ] Docker Desktop corriendo (ícono verde)
- [ ] `docker ps` muestra contenedores
- [ ] Backend health OK: http://localhost:8000/health
- [ ] DB aceptando conexiones (puerto 5432)
- [ ] Migraciones aplicadas (ver logs)
- [ ] Frontend accesible: http://localhost:8081
- [ ] No hay errores en `docker compose logs`

---

## 🆘 Última Opción: Reinicio Completo

```powershell
# 1. Detener todo
docker compose down -v

# 2. Limpiar Docker
docker system prune -a --volumes -f

# 3. Reiniciar Docker Desktop
# (Click derecho en ícono → Restart)

# 4. Rebuild desde cero
docker compose build --no-cache
docker compose up -d

# 5. Esperar 2 minutos y verificar
docker compose ps
docker compose logs backend
```

---

## 📞 Ayuda Adicional

Si nada funciona:

1. **Verificar requisitos de sistema**:
   - Windows 10/11 Pro, Enterprise o Education
   - WSL 2 instalado
   - Virtualización habilitada en BIOS

2. **Logs de Docker Desktop**:
   - Click en ícono de Docker → Troubleshoot → View logs

3. **Reinstalar Docker Desktop**:
   - https://www.docker.com/products/docker-desktop/

---

**Última actualización**: Enero 2025  
**Sistema**: Windows 10/11 + Docker Desktop + WSL2
