# 🔐 Configuración de SECRET_KEY y JWT_SECRET_KEY

**Fecha:** 06 Noviembre 2025  
**Problema:** Confusión entre SECRET_KEY y JWT_SECRET_KEY

---

## 📋 Resumen

El proyecto usa **DOS claves secretas diferentes** para propósitos distintos:

| Variable | Propósito | Usado Por | Requerido |
|----------|-----------|-----------|-----------|
| **SECRET_KEY** | Firma de URLs, tokens de email, CSRF | Email utils, main.py | ✅ SÍ |
| **JWT_SECRET_KEY** | Firma de tokens JWT (access/refresh) | JWT service, refresh.py | ✅ SÍ |

---

## 🔍 Análisis Detallado

### SECRET_KEY

**Ubicación en código:**
- `apps/backend/app/config/settings.py:44`

**Definición:**
```python
SECRET_KEY: SecretStr = SecretStr("change-me")
```

**Validación:**
```python
@field_validator("SECRET_KEY")
def validate_secret_key(cls, v: SecretStr) -> SecretStr:
    val = v.get_secret_value()
    if val == "change-me":
        raise ValueError("SECRET_KEY no puede ser 'change-me'...")
    if len(val) < 32:
        raise ValueError("SECRET_KEY debe tener ≥32 caracteres")
    return v
```

**Usado por:**
1. `apps/backend/app/main.py:83` - Firma de URLs
2. `apps/backend/app/api/email/email_utils.py:135` - Tokens de email (password reset, confirmación)

**Propósito:** 
- Firmar URLs de reset de contraseña
- Firmar tokens de confirmación de email
- Tokens de recuperación de cuenta

---

### JWT_SECRET_KEY

**Ubicación en código:**
- `apps/backend/app/config/settings.py:34`

**Definición:**
```python
JWT_SECRET_KEY: SecretStr | None = None  # HS*
```

**Usado por:**
1. `apps/backend/app/modules/identity/infrastructure/jwt_service.py:32-33` - Servicio JWT
2. `apps/backend/app/core/refresh.py:243` - Tokens de acceso y refresh

**Propósito:**
- Firmar tokens JWT de acceso (access tokens)
- Firmar tokens JWT de refresh
- Autenticación de usuarios

**Lógica de fallback:**
```python
# jwt_service.py línea 32-33
s_obj = getattr(app_settings, "JWT_SECRET", None) or getattr(
    app_settings, "JWT_SECRET_KEY", None
)

# Si no está configurada, usa default de desarrollo
if not secret:
    secret = "devsecretdevsecretdevsecret"
```

---

## ⚙️ Estado Actual del .env.example

```bash
# .env.example línea 23-25
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=devsecretdevsecretdevsecret  # ✅ Existe
SECRET_KEY=???  # ❌ NO EXISTE en .env.example
```

**Problema:** `.env.example` NO tiene `SECRET_KEY` pero el código lo requiere.

---

## ✅ Solución Correcta

### 1. Actualizar .env.example

**Agregar:**
```bash
# ==================== AUTH & SECURITY ====================
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=devsecretdevsecretdevsecret
SECRET_KEY=devsecretkeysecretkey32chars  # ← NUEVO

SESSION_COOKIE_NAME=sessionid
CSRF_COOKIE_NAME=csrf_token
COOKIE_DOMAIN=
COOKIE_SAMESITE=none
COOKIE_SECURE=false
```

### 2. Actualizar tu .env

**Opción A: Usar la misma clave para ambos (desarrollo)**
```bash
JWT_SECRET_KEY=_Cj7LOPZh_AdIibf-sDVuCLK1nOCpwTgAQAfgV0LLM_HZgSyZlkP1LbmGM4vHLNE
SECRET_KEY=_Cj7LOPZh_AdIibf-sDVuCLK1nOCpwTgAQAfgV0LLM_HZgSyZlkP1LbmGM4vHLNE
```

**Opción B: Usar claves diferentes (producción recomendado)**
```bash
# Para JWT (access/refresh tokens)
JWT_SECRET_KEY=_Cj7LOPZh_AdIibf-sDVuCLK1nOCpwTgAQAfgV0LLM_HZgSyZlkP1LbmGM4vHLNE

# Para email tokens, URLs firmadas
SECRET_KEY=zK9mP2xR5vN8wQ4tY7uI1oL3sH6jG0fD2aE5bC8
```

**Para generar claves:**
```bash
# Generar SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generar JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 📊 Comparación con CI/CD

**GitHub Actions CI (`.github/workflows/ci.yml:52`):**
```yaml
env:
  JWT_SECRET_KEY: "devsecrets@devsecretdevsecret"
  # ❌ NO define SECRET_KEY
```

**Problema:** Los tests fallarán si usan funciones que requieren `SECRET_KEY`.

**Solución:** Actualizar CI:
```yaml
env:
  JWT_SECRET_KEY: "devsecrets@devsecretdevsecret"
  SECRET_KEY: "devsecretkeysecretkey32chars"  # ← AGREGAR
```

---

## 🔐 Requerimientos de Seguridad

### Desarrollo
- ✅ `JWT_SECRET_KEY`: Puede usar default "devsecretdevsecretdevsecret"
- ✅ `SECRET_KEY`: Debe tener ≥32 caracteres, no puede ser "change-me"

### Producción
- ⚠️ `JWT_SECRET_KEY`: OBLIGATORIO, ≥32 caracteres, único
- ⚠️ `SECRET_KEY`: OBLIGATORIO, ≥32 caracteres, único
- ⚠️ Ambas claves deben ser DIFERENTES
- ⚠️ Nunca usar las mismas claves que desarrollo

**Validación automática:**
```python
# settings.py línea 247-248
if self.SECRET_KEY.get_secret_value() == "change-me":
    missing.append("SECRET_KEY (no usar 'change-me' en prod)")
```

---

## 🎯 Acciones Recomendadas

### Inmediato (Ahora)

1. **Actualizar `.env`:**
```bash
SECRET_KEY=_Cj7LOPZh_AdIibf-sDVuCLK1nOCpwTgAQAfgV0LLM_HZgSyZlkP1LbmGM4vHLNE
JWT_SECRET_KEY=devsecretdevsecretdevsecret  # Ya existe, dejar
```

2. **Reiniciar backend:**
```bash
docker restart backend
docker logs -f backend
```

### Corto Plazo (Esta semana)

3. **Actualizar `.env.example`:**
```bash
SECRET_KEY=devsecretkeysecretkey32chars  # ← AGREGAR esta línea
```

4. **Actualizar `.github/workflows/ci.yml`:**
```yaml
env:
  JWT_SECRET_KEY: "devsecrets@devsecretdevsecret"
  SECRET_KEY: "devsecretkeysecretkey32chars"  # ← AGREGAR
```

### Antes de Producción

5. **Generar claves únicas:**
```bash
# Producción - claves diferentes
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
```

6. **Guardar en gestor de secretos:**
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- Render Secret Files

---

## 🐛 Debugging

### Error: "SECRET_KEY no puede ser 'change-me'"
**Causa:** No has configurado SECRET_KEY en .env

**Solución:**
```bash
echo "SECRET_KEY=_Cj7LOPZh_AdIibf-sDVuCLK1nOCpwTgAQAfgV0LLM_HZgSyZlkP1LbmGM4vHLNE" >> .env
```

### Error: "JWT_SECRET_KEY no está configurada"
**Causa:** Falta JWT_SECRET_KEY o está vacío

**Solución:**
```bash
echo "JWT_SECRET_KEY=devsecretdevsecretdevsecret" >> .env
```

### Verificar configuración actual
```bash
docker exec backend python -c "
from app.config.settings import settings
print('SECRET_KEY length:', len(settings.SECRET_KEY.get_secret_value()))
jwt = getattr(settings, 'JWT_SECRET_KEY', None)
if jwt:
    print('JWT_SECRET_KEY length:', len(jwt.get_secret_value()))
else:
    print('JWT_SECRET_KEY: Not configured')
"
```

---

## 📚 Referencias en Código

### SECRET_KEY usado en:
- [apps/backend/app/main.py:83](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/main.py#L83)
- [apps/backend/app/api/email/email_utils.py:135](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/api/email/email_utils.py#L135)

### JWT_SECRET_KEY usado en:
- [apps/backend/app/modules/identity/infrastructure/jwt_service.py:32](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/modules/identity/infrastructure/jwt_service.py#L32)
- [apps/backend/app/core/refresh.py:243](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/core/refresh.py#L243)

### Settings:
- [apps/backend/app/config/settings.py:34-55](file:///c:/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend/app/config/settings.py#L34-L55)

---

**Última actualización:** 06 Noviembre 2025  
**Estado:** Documentación completa  
**Acción requerida:** Actualizar `.env` con SECRET_KEY
