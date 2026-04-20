# Configuración de Systemd Services - Variables de Entorno

## 🔒 Seguridad: Environment Files

Los systemd services deben obtener credenciales de archivos separados, NO hardcodeados en el `.service`.

### Estructura Recomendada

```
/etc/gestiq/
├── importador-fast.env         # 600: gestiq:gestiq
├── importador-deep.env         # 600: gestiq:gestiq
├── worker-imports.env          # legado
├── worker-notifications.env    # 600: gestiq:gestiq
└── api.env                     # 600: gestiq:gestiq (si aplica)
```

### Paso 1: Crear el archivo de entorno

```bash
# Como root:
mkdir -p /etc/gestiq
touch /etc/gestiq/worker-imports.env
chmod 600 /etc/gestiq/worker-imports.env
chown gestiq:gestiq /etc/gestiq/worker-imports.env
```

### Paso 2: Agregar variables criticas

#### Archivo: `/etc/gestiq/importador-fast.env`

```bash
ENVIRONMENT=production

DATABASE_URL=postgresql://gestiq:ACTUAL_PASSWORD@db.internal:5432/gestiqcloud
DB_DSN=postgresql://gestiq:ACTUAL_PASSWORD@db.internal:5432/gestiqcloud
REDIS_URL=redis://cache.internal:6379/1

SECRET_KEY=REEMPLAZAR_CON_UNA_CLAVE_LARGA_Y_ALEATORIA
FRONTEND_URL=https://www.gestiqcloud.com
TENANT_NAMESPACE_UUID=00000000-0000-0000-0000-000000000000

IMPORTS_ENABLED=1
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
COOKIE_DOMAIN=.gestiqcloud.com

UPLOADS_DIR=/opt/gestiqcloud/uploads
IMPORTADOR_PAYLOAD_DIR=/opt/gestiqcloud/uploads/_importador_payloads
```

#### Archivo: `/etc/gestiq/importador-deep.env`

```bash
ENVIRONMENT=production

DATABASE_URL=postgresql://gestiq:ACTUAL_PASSWORD@db.internal:5432/gestiqcloud
DB_DSN=postgresql://gestiq:ACTUAL_PASSWORD@db.internal:5432/gestiqcloud
REDIS_URL=redis://cache.internal:6379/1

SECRET_KEY=REEMPLAZAR_CON_UNA_CLAVE_LARGA_Y_ALEATORIA
FRONTEND_URL=https://www.gestiqcloud.com
TENANT_NAMESPACE_UUID=00000000-0000-0000-0000-000000000000

IMPORTS_ENABLED=1
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
COOKIE_DOMAIN=.gestiqcloud.com

UPLOADS_DIR=/opt/gestiqcloud/uploads
IMPORTADOR_PAYLOAD_DIR=/opt/gestiqcloud/uploads/_importador_payloads

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT=30
OLLAMA_HEALTH_TIMEOUT=5
OLLAMA_MAX_CONCURRENCY=4
```

**Archivo: `/etc/gestiq/worker-imports.env`**
```bash
# Database
DB_DSN=postgresql://gestiq:ACTUAL_PASSWORD@db.internal:5432/gestiqcloud

# Redis
REDIS_URL=redis://cache.internal:6379/1

# Workers
IMPORTS_ENABLED=1
IMPORTS_RUNNER_MODE=celery

# Environment
ENVIRONMENT=production

# API Settings (if needed)
DEFAULT_FROM_EMAIL=noreply@gestiqcloud.com
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
```

### Paso 3: Actualizar el service

**Archivo: `gestiq-importador-fast.service`**
```ini
[Service]
EnvironmentFile=/etc/gestiq/importador-fast.env
```

**Archivo: `gestiq-importador-deep.service`**
```ini
[Service]
EnvironmentFile=/etc/gestiq/importador-deep.env
```

**Archivo legado: `gestiq-worker-imports.service`**
```ini
[Service]
EnvironmentFile=/etc/gestiq/worker-imports.env

# Remove hardcoded variables like:
# Environment="DB_DSN=..."
# Environment="REDIS_URL=..."
```

### Verificar que funciona

```bash
# Listar variables del service
systemctl show gestiq-worker-imports -p Environment

# Ver logs
journalctl -u gestiq-worker-imports -f

# Reiniciar
systemctl restart gestiq-worker-imports
```

## 📋 Variables por Service

### gestiq-importador-fast.service

**Requeridas:**
- `REDIS_URL` - Redis para Celery
- `DATABASE_URL` - PostgreSQL database
- `DB_DSN` - alias legacy soportado por compatibilidad
- `SECRET_KEY` - clave de aplicacion
- `FRONTEND_URL` - URL principal del frontend
- `TENANT_NAMESPACE_UUID` - namespace fijo para tenants
- `IMPORTS_ENABLED` - habilitar importador (1 o 0)

**Opcionales:**
- `ENVIRONMENT` - "production" o "development"
- `UPLOADS_DIR` - almacenamiento persistente
- `IMPORTADOR_PAYLOAD_DIR` - payloads temporales del importador
- `CORS_ORIGINS`
- `COOKIE_DOMAIN`

### gestiq-importador-deep.service

**Requeridas:**
- Todas las de `gestiq-importador-fast.service`

**Opcionales recomendadas:**
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT`
- `OLLAMA_HEALTH_TIMEOUT`
- `OLLAMA_MAX_CONCURRENCY`

### gestiq-worker-imports.service (legado)

**Requeridas:**
- `REDIS_URL`
- `DB_DSN`
- `IMPORTS_ENABLED`
- `IMPORTS_RUNNER_MODE`

### gestiq-worker-notifications.service (si existe)

**Requeridas:**
- `REDIS_URL`
- `DEFAULT_FROM_EMAIL`

**Opcionales:**
- `SLACK_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`

## 🔐 Mejores Prácticas

1. ✅ **Nunca hardcodear credentials en `.service`**
2. ✅ **Usar `EnvironmentFile` para configuración dinámica**
3. ✅ **Permisos 600** en archivos de configuración
4. ✅ **Owner debe ser el usuario del service** (gestiq:gestiq)
5. ✅ **No guardar archivos en /etc/gestiq en git**
6. ✅ **Documentar variables requeridas en README**

## Deployment Checklist

- [ ] Crear `/etc/gestiq/worker-imports.env` con permisos 600
- [ ] Crear `/etc/gestiq/importador-fast.env` con permisos 600
- [ ] Crear `/etc/gestiq/importador-deep.env` con permisos 600
- [ ] Actualizar `gestiq-worker-imports.service` para usar `EnvironmentFile`
- [ ] Instalar `gestiq-importador-fast.service`
- [ ] Instalar `gestiq-importador-deep.service`
- [ ] Remover hardcoded `Environment=` lines del service
- [ ] Detener y deshabilitar `gestiq-imports-worker` legado
- [ ] Probar: `systemctl start gestiq-importador-fast gestiq-importador-deep`
- [ ] Verificar: `journalctl -u gestiq-importador-fast | grep ERROR`
- [ ] Verificar: `journalctl -u gestiq-importador-deep | grep ERROR`

## Recuperación ante Errores

```bash
# Si falta el archivo .env:
# Error: "No such file or directory"
# Solución: crear archivo con variables requeridas

# Si permisos incorrectos:
# Error: "Permission denied"
# Solución: chmod 600 /etc/gestiq/worker-imports.env

# Si variable mal formada:
# Error: "REDIS_URL=" (vacío)
# Solución: verificar archivo con 'cat /etc/gestiq/worker-imports.env'
```

---

**Último update:** 15 Enero 2026
**Status:** 🟡 MODERADO - En implementación
