# Migración JWT: localStorage → Cookies HttpOnly

## 📋 Resumen

Migración de tokens JWT desde `localStorage` (vulnerable a XSS) a **cookies HttpOnly** (seguras).

**Estado**: ✅ Código backend implementado | ⚠️ Frontend pendiente

---

## 🔧 Cambios en Backend

### 1. Nuevos Módulos Creados

#### `app/core/auth_cookies.py`
Utilidades para manejo de cookies seguras:
- `set_access_token_cookie()` - Establece access token en cookie
- `set_refresh_token_cookie()` - Establece refresh token en cookie
- `get_token_from_cookie()` - Extrae token desde cookie
- `clear_auth_cookies()` - Elimina cookies (logout)
- `get_token_from_cookie_or_header()` - **Migración gradual**: Acepta cookie O header

#### `app/core/security_cookies.py`
Security guards actualizados:
- `get_current_user_from_cookie()` - Dependency para rutas protegidas
- `get_current_active_tenant_user()` - Specific para tenant
- `get_current_admin_user()` - Specific para admin

### 2. Ejemplo de Login Actualizado

**Antes** (vulnerab

le):
```python
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # ... validación ...
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # ❌ Cliente guarda en localStorage
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

**Después** (seguro):
```python
from app.core.auth_cookies import set_access_token_cookie, set_refresh_token_cookie

@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,  # ✅ Agregar Response
    db: Session = Depends(get_db)
):
    # ... validación ...
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # ✅ Setear cookies HttpOnly
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)

    # ✅ Retornar solo datos de usuario (sin tokens)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id
        }
    }
```

### 3. Ejemplo de Ruta Protegida

**Antes**:
```python
from fastapi import Header

@router.get("/protected")
def protected_route(authorization: str = Header()):
    # Extraer token manualmente
    token = authorization.replace("Bearer ", "")
    # ...
```

**Después**:
```python
from app.core.security_cookies import get_current_active_tenant_user

@router.get("/protected")
def protected_route(
    current_user = Depends(get_current_active_tenant_user)
):
    # ✅ Usuario ya validado desde cookie
    return {"user_id": current_user.id}
```

### 4. Logout

**Antes**:
```python
@router.post("/logout")
def logout():
    # ❌ Frontend debe borrar localStorage manualmente
    return {"message": "Logged out"}
```

**Después**:
```python
from app.core.auth_cookies import clear_auth_cookies

@router.post("/logout")
def logout(response: Response):
    # ✅ Eliminar cookies automáticamente
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
```

---

## 🎨 Cambios en Frontend

### 1. Eliminar localStorage

**apps/tenant/src/auth/AuthContext.tsx**

**Antes** (❌ INSEGURO):
```typescript
// Login
const login = async (email: string, password: string) => {
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  })

  const data = await res.json()

  // ❌ XSS vulnerable
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
}

// Fetch protegido
const fetchProtected = async (url: string) => {
  const token = localStorage.getItem('access_token')  // ❌

  return fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
}
```

**Después** (✅ SEGURO):
```typescript
// Login
const login = async (email: string, password: string) => {
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    credentials: 'include',  // ✅ Envía/recibe cookies
    body: JSON.stringify({ email, password })
  })

  const data = await res.json()

  // ✅ NO guardar tokens (están en cookies HttpOnly)
  // Solo guardar datos de usuario si es necesario
  setUser(data.user)
}

// Fetch protegido
const fetchProtected = async (url: string) => {
  // ✅ Cookie se envía automáticamente
  return fetch(url, {
    credentials: 'include'  // ✅ Browser envía cookie HttpOnly
  })
}

// Logout
const logout = async () => {
  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include'
  })

  // ✅ Cookie eliminada por backend
  setUser(null)
}
```

### 2. Actualizar HTTP Client

**apps/tenant/src/lib/http.ts**

**Antes**:
```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1'
})

// Interceptor para agregar token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')  // ❌
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

**Después**:
```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true  // ✅ Envía cookies en cada request
})

// ✅ NO necesita interceptor para agregar token
// Cookie se envía automáticamente
```

### 3. Actualizar Axios/Fetch Globales

**Buscar y reemplazar**:
```bash
# En todos los archivos TS/TSX:

# 1. Eliminar localStorage de tokens
rg "localStorage.setItem.*token" apps/tenant/src apps/admin/src
rg "localStorage.getItem.*token" apps/tenant/src apps/admin/src

# 2. Agregar credentials: 'include'
rg "fetch\(" apps/tenant/src apps/admin/src
```

---

## 🧪 Testing

### Backend

```python
# apps/backend/app/tests/test_auth_cookies.py
from app.core.auth_cookies import set_access_token_cookie
from fastapi.responses import Response

def test_set_access_token_cookie():
    response = Response()
    token = "test_token_123"

    set_access_token_cookie(response, token)

    # Verificar que cookie existe
    assert "access_token" in response.headers.get("set-cookie", "")
    assert "HttpOnly" in response.headers.get("set-cookie", "")
    assert "SameSite=lax" in response.headers.get("set-cookie", "")
```

### Frontend

```typescript
// apps/tenant/src/auth/AuthContext.test.tsx
import { renderHook, act } from '@testing-library/react'
import { useAuth } from './AuthContext'

test('login sets cookie instead of localStorage', async () => {
  const { result } = renderHook(() => useAuth())

  await act(async () => {
    await result.current.login('user@test.com', 'password123')
  })

  // ✅ localStorage NO debe tener tokens
  expect(localStorage.getItem('access_token')).toBeNull()
  expect(localStorage.getItem('refresh_token')).toBeNull()
})
```

---

## ⚠️ Compatibilidad Retroactiva

Para evitar romper el sistema durante la migración, el backend **acepta tokens desde cookie O header**:

```python
# app/core/auth_cookies.py
def get_token_from_cookie_or_header(request: Request) -> Optional[str]:
    # 1. Preferencia: Cookie (seguro)
    token = get_token_from_cookie(request)
    if token:
        return token

    # 2. Fallback: Authorization header (legacy)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "").strip()

    return None
```

**Estrategia de migración**:
1. ✅ **Fase 1** (Semana 1): Deploy backend con soporte dual
2. ⚠️ **Fase 2** (Semana 2): Deploy frontend usando cookies
3. 🔒 **Fase 3** (Semana 3): Eliminar soporte de header (solo cookies)

---

## 📝 Checklist de Implementación

### Backend ✅
- [x] Crear `app/core/auth_cookies.py`
- [x] Crear `app/core/security_cookies.py`
- [ ] Actualizar endpoints de login en:
  - [ ] `app/api/v1/tenant/auth.py`
  - [ ] `app/api/v1/admin/auth.py`
  - [ ] `app/modules/identity/interface/http/tenant.py`
- [ ] Actualizar endpoints de logout
- [ ] Actualizar refresh token endpoint
- [ ] Tests unitarios

### Frontend Tenant ⚠️
- [ ] Actualizar `apps/tenant/src/auth/AuthContext.tsx`
- [ ] Actualizar `apps/tenant/src/lib/http.ts`
- [ ] Eliminar `localStorage.setItem/getItem` de tokens
- [ ] Agregar `credentials: 'include'` en todos los fetch/axios
- [ ] Actualizar servicios API:
  - [ ] `src/modules/*/services.ts`
- [ ] Tests

### Frontend Admin ⚠️
- [ ] Actualizar `apps/admin/src/auth/AuthContext.tsx`
- [ ] Actualizar `apps/admin/src/lib/http.ts`
- [ ] Eliminar localStorage de tokens
- [ ] Agregar `credentials: 'include'`
- [ ] Tests

---

## 🔒 Configuración de Producción

**render.yaml** (ya configurado):
```yaml
# Backend
envVars:
  - key: COOKIE_SECURE
    value: "true"  # ✅ Solo HTTPS
  - key: COOKIE_SAMESITE
    value: "lax"   # ✅ Previene CSRF
  - key: COOKIE_DOMAIN
    value: ".gestiqcloud.com"  # ✅ Compartir entre subdominios
```

**CORS** (ya configurado):
```yaml
- key: CORS_ALLOW_CREDENTIALS
  value: "true"  # ✅ Permite cookies cross-origin
- key: CORS_ORIGINS
  value: "https://gestiqcloud.com,https://admin.gestiqcloud.com"
```

---

## 📊 Beneficios

| Antes (localStorage) | Después (Cookies HttpOnly) |
|---------------------|---------------------------|
| ❌ XSS puede robar tokens | ✅ JS no puede acceder a cookies |
| ❌ CSRF posible | ✅ SameSite=lax previene CSRF |
| ❌ Tokens expuestos en DevTools | ✅ Cookies ocultas |
| ❌ Manual token refresh | ✅ Automático via cookies |
| ❌ Logout requiere client-side clear | ✅ Server-side logout |

---

## 🆘 Troubleshooting

### "Cookie not being set"

**Solución**: Verificar CORS y `COOKIE_SECURE`:
```python
# settings.py
COOKIE_SECURE = False  # En desarrollo (HTTP)
COOKIE_SECURE = True   # En producción (HTTPS)
```

### "401 Unauthorized even after login"

**Solución**: Frontend debe enviar `credentials: 'include'`:
```typescript
fetch('/api/v1/protected', {
  credentials: 'include'  // ✅ REQUERIDO
})
```

### "CORS error with cookies"

**Solución**: Backend debe tener:
```python
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,  # ✅ REQUERIDO para cookies
    allow_origins=["https://tenant.com"]
)
```

---

**Última actualización**: 2025-11-06
**Autor**: Auditoría Técnica
