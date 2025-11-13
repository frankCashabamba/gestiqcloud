# 🚀 INSTRUCCIONES DE IMPLEMENTACIÓN DE MEJORAS

Este documento describe los pasos para aplicar las mejoras implementadas en la auditoría técnica.

---

## ✅ MEJORAS IMPLEMENTADAS (Automáticas)

Las siguientes mejoras ya están implementadas en el código:

### **Backend** ✅
1. ✅ **mypy + type checking** - Configurado en `pyproject.toml`
2. ✅ **Bandit (SAST)** - Agregado a pre-commit hooks
3. ✅ **Rate limiting por endpoint** - Middleware implementado en `app/middleware/endpoint_rate_limit.py`
4. ✅ **Coverage configurado** - pytest-cov con mínimo 40%
5. ✅ **Pre-commit mejorado** - mypy, bandit, ruff, black, isort

### **Frontend** ✅
1. ✅ **ESLint configurado** - `.eslintrc.json` en tenant y admin
2. ✅ **Lazy loading de rutas** - Implementado en `App.tsx` con `React.lazy()`
3. ✅ **Code splitting** - Chunks manuales en `vite.config.ts`
4. ✅ **Tree shaking MUI** - Separación de vendor chunks

---

## 📦 INSTALACIÓN DE DEPENDENCIAS

### **Backend (Python)**

```bash
cd apps/backend

# Instalar dependencias de desarrollo
pip install --upgrade pip
pip install mypy bandit pytest-cov

# Instalar pre-commit hooks
cd ../..  # Volver a root
pip install pre-commit
pre-commit install

# Ejecutar pre-commit manualmente (primera vez)
pre-commit run --all-files
```

**Dependencias agregadas** (agregar a `requirements-dev.txt`):
```txt
mypy>=1.11.0
bandit>=1.7.9
pytest-cov>=5.0.0
pre-commit>=3.8.0
types-passlib>=1.7.7
types-PyYAML>=6.0.1
```

---

### **Frontend (Node.js)**

#### **Tenant App**
```bash
cd apps/tenant

# Instalar ESLint y plugins
npm install --save-dev \
  eslint@^8.57.0 \
  @typescript-eslint/parser@^7.0.0 \
  @typescript-eslint/eslint-plugin@^7.0.0 \
  eslint-plugin-react@^7.35.0 \
  eslint-plugin-react-hooks@^4.6.0 \
  eslint-plugin-jsx-a11y@^6.9.0

# Ejecutar lint
npm run lint

# Fix automático
npm run lint:fix

# Ejecutar typecheck + lint
npm run check
```

#### **Admin App**
```bash
cd apps/admin

# Mismas dependencias que tenant
npm install --save-dev \
  eslint@^8.57.0 \
  @typescript-eslint/parser@^7.0.0 \
  @typescript-eslint/eslint-plugin@^7.0.0 \
  eslint-plugin-react@^7.35.0 \
  eslint-plugin-react-hooks@^4.6.0 \
  eslint-plugin-jsx-a11y@^6.9.0

npm run lint
```

---

## 🧪 VERIFICACIÓN

### **Backend**

```bash
cd apps/backend

# 1. Ejecutar linters
ruff check app/
black --check app/
isort --check app/

# 2. Type checking
mypy app/ --config-file=pyproject.toml

# 3. Security scan
bandit -r app/ -c pyproject.toml

# 4. Tests con coverage
pytest --cov=app --cov-report=term --cov-report=html

# 5. Ver reporte de coverage
# Abrir: apps/backend/htmlcov/index.html
```

### **Frontend**

```bash
# Tenant
cd apps/tenant
npm run typecheck  # TypeScript
npm run lint       # ESLint
npm run build      # Verifica code splitting

# Admin
cd apps/admin
npm run typecheck
npm run lint
npm run build
```

---

## ⚠️ ERRORES ESPERADOS Y CÓMO RESOLVERLOS

### **mypy: Errores de tipos**

Si mypy reporta errores:

1. **Imports faltantes**: Agregar a `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = "nombre_paquete.*"
ignore_missing_imports = true
```

2. **Tipos Any**: Gradualmente agregar type hints:
```python
# ❌ Antes
def process_data(data):
    return data

# ✅ Después
def process_data(data: dict[str, Any]) -> dict[str, Any]:
    return data
```

### **ESLint: Warnings masivos**

Si hay muchos warnings:

1. **Ejecutar fix automático** primero:
```bash
npm run lint:fix
```

2. **Warnings aceptables temporalmente**: En `.eslintrc.json`:
```json
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",  // warn en vez de error
    "jsx-a11y/click-events-have-key-events": "off"  // desactivar temporalmente
  }
}
```

### **Build falla por memoria**

Si Vite falla en build:

```bash
# Aumentar memoria de Node.js
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

---

## 🎯 PRÓXIMOS PASOS (Tareas Manuales)

Las siguientes tareas requieren implementación manual:

### **1. Mover JWT a cookies HttpOnly** 🔴 CRÍTICO
**Esfuerzo**: M (4 días)
**Archivos a modificar**:
- Backend: `app/modules/identity/application/auth.py`
- Backend: `app/api/v1/tenant/auth.py`
- Frontend: `apps/tenant/src/auth/AuthContext.tsx`

**Pasos**:
1. Backend: Modificar endpoints de login para setear cookie en respuesta
2. Frontend: Eliminar `localStorage.setItem('token')`, usar `credentials: 'include'`
3. Backend: Leer token desde cookie en middleware

### **2. Eliminar routers legacy duplicados** 🔴 ALTO
**Esfuerzo**: M (4 días)
**Archivos a modificar**:
- `apps/backend/app/main.py` (líneas 198-428)
- Validar cobertura de tests antes de eliminar

**Pasos**:
1. Revisar cada router legacy vs. módulo moderno
2. Ejecutar tests: `pytest app/tests/`
3. Eliminar montaje de routers legacy en `main.py`
4. Eliminar archivos en `app/routers/` (excepto admin/, tenant/)

### **3. Tests con coverage mínimo 60%** ⚠️ ALTO
**Esfuerzo**: L (15 días)
**Archivos a crear**:
- `apps/backend/app/modules/*/tests/test_*.py`
- `apps/tenant/src/modules/*/*.test.tsx`

**Priorizar**:
- Backend: identity, imports, ventas, compras
- Frontend: auth, ventas, importador

### **4. Migrar a Alembic único** ⚠️ MEDIO
**Esfuerzo**: M (4 días)
**Pasos**:
1. Archivar `ops/migrations/` → `ops/_archive_legacy/`
2. Generar migración Alembic consolidada
3. Actualizar `prod.py` para deshabilitar legacy migrations
4. Documentar en `ops/migrations/README.md`

---

## 📊 MÉTRICAS DE ÉXITO

### **Backend**
- [ ] Coverage ≥ 40% (objetivo: 60%)
- [ ] mypy pasa sin errores en `app/platform/` y `app/modules/identity/`
- [ ] Bandit: 0 issues de severidad MEDIUM/HIGH
- [ ] Rate limit: Login limitado a 10 req/min por IP

### **Frontend**
- [ ] ESLint: ≤ 50 warnings
- [ ] Bundle inicial ≤ 500 KB (actual: ~800-900 KB)
- [ ] Lighthouse Performance ≥ 80
- [ ] Lazy loading: 5+ chunks generados en build

---

## 🆘 SOPORTE

Si encuentras problemas:

1. **Logs de mypy**: `mypy app/ > mypy-report.txt`
2. **Logs de ESLint**: `npm run lint > eslint-report.txt`
3. **Coverage HTML**: Abrir `htmlcov/index.html`

**Checklist de troubleshooting**:
- ✅ Python 3.11 instalado
- ✅ Node.js 20 instalado
- ✅ Virtual environment activado (`.venv`)
- ✅ `pip install -r requirements.txt` ejecutado
- ✅ `npm install` ejecutado en apps/tenant y apps/admin

---

**Última actualización**: 2025-11-06
**Autor**: Auditoría Técnica Automatizada
