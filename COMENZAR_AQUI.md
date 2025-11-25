# 🚀 REFACTORIZACIÓN BACKEND - COMIENZA AQUÍ

## ¿Qué vas a hacer?

Renombrar **TODOS** los modelos/esquemas/módulos de español a inglés:
- **proveedores** → **suppliers**
- **gastos** → **expenses**
- **empresa** → **company**
- **rrhh** → **hr**
- **usuarios** → **users**

## ⏱️ Tiempo Total: ~75 minutos

---

## 📖 LEE ESTO PRIMERO (5 minutos)

### Opción A: Si eres impaciente
Lee **REFACTOR_QUICK_START.md** - Tiene todo paso a paso (recomendado)

### Opción B: Si quieres entender todo
Lee estos en orden:
1. **README_REFACTORING.md** - Resumen ejecutivo completo
2. **REFACTOR_EXECUTABLE.md** - Detalles técnicos
3. **REFACTOR_MAPPING.txt** - Mapeo visual de cambios

### Opción C: Si necesitas referencia técnica
Consulta **REFACTOR_ANALYSIS.md** - Análisis profundo del codebase

---

## 🎯 PLAN DE 5 PASOS (75 minutos)

```
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: PREPARACIÓN (5 min)                                     │
│ • git commit y crear rama                                       │
│ • Verificar estado actual                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: AUTOMATIZACIÓN (12 min)                                 │
│ • python refactor_script.py --analyze                           │
│ • python refactor_script.py --execute                           │
│ • python refactor_script.py --verify                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: RENOMBRAMIENTOS MANUALES (20 min)                       │
│ • Renombrar directorios modules/ (PowerShell)                  │
│ • Renombrar archivos schemas/                                   │
│ • Eliminar archivos compat/legacy                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: LIMPIEZA MANUAL (23 min)                                │
│ • Revisar archivos críticos (router.py, main.py, base.py)     │
│ • Limpiar docstrings en español                                 │
│ • Actualizar tests                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: VERIFICACIÓN (15 min)                                   │
│ • Buscar referencias residuales                                 │
│ • Correr tests (pytest)                                         │
│ • Commit y subir rama                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ INICIO RÁPIDO (COPY-PASTE)

```bash
# 1. Navegar a repo
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto

# 2. Git setup
git add .
git commit -m "Pre-refactor checkpoint"
git checkout -b refactor/spanish-to-english

# 3. Análisis (solo visualizar)
python refactor_script.py --analyze

# 4. EJECUTAR CAMBIOS AUTOMÁTICOS (⚠️ PUNTO DE NO RETORNO)
python refactor_script.py --execute
# Responder "y" cuando pregunte

# 5. Verificar
python refactor_script.py --verify

# 6. VER REFACTOR_QUICK_START.md PARA PASOS MANUALES
# (Ya hizo los automáticos, ahora ve a sección 4 del quick start)
```

---

## 📋 CHECKLIST PRE-REFACTORING

Antes de ejecutar **refactor_script.py --execute**:

- [ ] Git está limpio: `git status` → "working tree clean"
- [ ] Rama creada: `git branch` → ves "refactor/spanish-to-english"
- [ ] Tests pasan: `pytest tests/ -v` → todos GREEN
- [ ] Leíste al menos REFACTOR_QUICK_START.md
- [ ] Tienes PowerShell abierto para comandos manuales
- [ ] Tienes ~75 minutos libres

---

## 🗂️ ARCHIVOS QUE NECESITAS

| Archivo | Para Qué | Importancia |
|---------|----------|-------------|
| **REFACTOR_QUICK_START.md** | Guía paso a paso detallada | ⭐⭐⭐ CRÍTICO |
| **refactor_script.py** | Automatizar cambios | ⭐⭐⭐ CRÍTICO |
| **README_REFACTORING.md** | Resumen ejecutivo | ⭐⭐ IMPORTANTE |
| **REFACTOR_EXECUTABLE.md** | Detalles técnicos | ⭐⭐ IMPORTANTE |
| **REFACTOR_MAPPING.txt** | Referencia visual | ⭐ REFERENCIA |
| **REFACTOR_PLAN.md** | Plan general | ⭐ REFERENCIA |
| **REFACTOR_ANALYSIS.md** | Análisis codebase | ⭐ REFERENCIA |

---

## ⚠️ COSAS MUY IMPORTANTES

### 1. NO PUEDES DESHACER FÁCILMENTE
Una vez que ejecutes `--execute`, los cambios son muchos. Pero puedes revertir:
```bash
git reset --hard HEAD~1
```

### 2. ALGUNOS CAMBIOS SON MANUALES
El script hace automático. Tú haces:
- Renombrar directorios
- Eliminar archivos
- Limpiar docstrings
- Revisar críticos

### 3. TESTS DEBEN PASAR AL FINAL
```bash
pytest tests/ -v
```

### 4. LOS DATOS DE BD NO SE PIERDEN
Solo se renombran columnas/tablas. Los datos quedan intactos.

---

## 🆘 SI ALGO SALE MAL

```bash
# Opción 1: Revertir el último commit
git reset --hard HEAD~1

# Opción 2: Volver a main completamente
git checkout main
git reset --hard origin/main

# Opción 3: Revisar qué cambios se hicieron
git log --oneline -10
git diff HEAD~1
```

---

## ✅ CÓMO SABER QUE TODO ESTÁ BIEN

Después de Paso 5, verifica:

```bash
# 1. Sin referencias a módulos españoles
grep -r "from app.modules.proveedores\|gastos\|empresa" apps/backend/app/
# Resultado: (nada, vacío)

# 2. Sin aliases deprecated
grep -r 'alias="proveedor_id"\|alias="categoria_gasto_id"' apps/backend/app/
# Resultado: (nada, vacío)

# 3. Tests verdes
pytest tests/ -v
# Resultado: ✅ ALL TESTS PASSED

# 4. Archivos legacy NO existen
ls apps/backend/app/models/company/empresa.py 2>/dev/null
# Resultado: (file not found)
```

---

## 🎓 ¿POR QUÉ HACER ESTO?

✅ **Consistencia**: Todo el código en un idioma
✅ **Mantenibilidad**: Menos confusión de nombres
✅ **Estándar industrial**: Convención global de código en inglés
✅ **Colaboración**: Más fácil para desarrolladores internacionales
✅ **Futuro**: Base limpia para nuevas features

---

## 📚 ESTRUCTURA DE DOCUMENTOS

```
COMENZAR_AQUI.md ⭐ ← TÚ ESTÁS AQUÍ
├─ REFACTOR_QUICK_START.md ⭐ (Lee esto primero)
├─ refactor_script.py (Ejecuta esto)
├─ README_REFACTORING.md (Resumen)
├─ REFACTOR_EXECUTABLE.md (Detalles)
├─ REFACTOR_MAPPING.txt (Referencia)
├─ REFACTOR_PLAN.md (Plan)
└─ REFACTOR_ANALYSIS.md (Análisis)
```

---

## 🎬 PRÓXIMO PASO

### ➡️ Opción 1: VÍA RÁPIDA (RECOMENDADO)
1. Abre **REFACTOR_QUICK_START.md**
2. Sigue sección 0-1 (Preparación + Análisis)
3. Vuelve aquí si tienes dudas

### ➡️ Opción 2: VÍA COMPLETA
1. Lee **README_REFACTORING.md** (10 min)
2. Abre **REFACTOR_EXECUTABLE.md**
3. Sigue paso a paso

### ➡️ Opción 3: VÍA TÉCNICA
1. Abre **REFACTOR_ANALYSIS.md**
2. Entiende lo que necesita cambiar
3. Luego ejecuta con confianza

---

## 💡 PRO TIPS

✨ **Tip 1**: Mantén PowerShell y terminal bash abiertas simultáneamente

✨ **Tip 2**: Haz pequeños commits después de cada sección

✨ **Tip 3**: Si hay error, mejor revertir y empezar de nuevo

✨ **Tip 4**: Los docstrings en archivos .md pueden quedarse en español

✨ **Tip 5**: Verifica que VS Code/editor no cache imports antiguos

---

## 📞 TROUBLESHOOTING RÁPIDO

| Problema | Solución |
|----------|----------|
| "File not found" al renombrar | Asegúrate de que exista primero (`ls`) |
| Import circular error | Revisa `__init__.py` en módulos |
| Tests fallan | Verifica imports de tests correspondan |
| Alembic error | Regenera: `alembic revision --autogenerate` |
| Git conflict | Resuelve con `git status` y edita archivos |

---

## 🚀 ¡LISTO PARA EMPEZAR!

**Próximo paso**: Abre **REFACTOR_QUICK_START.md** y comienza en sección 0 (Preparación)

**Duración**: ~75 minutos
**Dificultad**: Media (automatizado + manual)
**Reversible**: SÍ (git reset)

---

**¿Preguntas?** Consulta los archivos de referencia arriba.
**¿Listo?** 👉 Abre REFACTOR_QUICK_START.md
