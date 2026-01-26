# Configuración de Systemd Services - Variables de Entorno

## 🔒 Seguridad: Environment Files

Los systemd services deben obtener credenciales de archivos separados, NO hardcodeados en el `.service`.

### Estructura Recomendada

```
/etc/gestiq/
├── worker-imports.env          # 600: gestiq:gestiq
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

### Paso 2: Agregar variables críticas

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

**Archivo: `gestiq-worker-imports.service`**
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

### gestiq-worker-imports.service

**Requeridas:**
- `REDIS_URL` - Redis para Celery
- `DB_DSN` - PostgreSQL database
- `IMPORTS_ENABLED` - Habilitar módulo (1 o 0)
- `IMPORTS_RUNNER_MODE` - "celery" o "local"

**Opcionales:**
- `ENVIRONMENT` - "production" o "development"

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
- [ ] Actualizar `gestiq-worker-imports.service` para usar `EnvironmentFile`
- [ ] Remover hardcoded `Environment=` lines del service
- [ ] Probar: `systemctl start gestiq-worker-imports`
- [ ] Verificar: `journalctl -u gestiq-worker-imports | grep ERROR`

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
