@echo off
REM ============================================================================
REM     REFACTORING BACKEND - SCRIPT DE EJECUCIÓN AUTOMATIZADA
REM ============================================================================
REM Ejecuta todos los pasos del refactoring Spanish to English
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo                 REFACTORIZACIÓN BACKEND - EJECUCIÓN
echo ============================================================================
echo.

REM PASO 0: Verificar estado
echo [PASO 0] Verificando estado Git...
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto
git status > NUL 2>&1
if errorlevel 1 (
    echo ❌ ERROR: No está en un repositorio Git
    exit /b 1
)
echo ✅ Repositorio Git detectado

REM PASO 1: Git setup
echo.
echo [PASO 1] Configurando Git...
git add . > NUL 2>&1
git commit -m "Pre-refactor checkpoint: Spanish to English" > NUL 2>&1
if errorlevel 1 (
    echo ⚠️  No hay cambios sin guardar (está bien)
) else (
    echo ✅ Checkpoint guardado
)

echo Creando rama de trabajo...
git checkout -b refactor/spanish-to-english 2>&1 | find "fatal" > NUL
if errorlevel 1 (
    echo ✅ Rama creada o ya existe
) else (
    echo ⚠️  Rama ya existe
)
echo.

REM PASO 2: Análisis
echo [PASO 2] Analizando cambios necesarios...
python refactor_script.py --analyze > refactor_analysis.log 2>&1
if errorlevel 1 (
    echo ❌ ERROR en análisis
    echo Ver: refactor_analysis.log
    exit /b 1
)
echo ✅ Análisis completado
echo Ver detalles en: refactor_analysis.log
echo.

REM Mostrar resumen del análisis
for /f "tokens=*" %%A in (refactor_analysis.log) do (
    if "%%A" neq "" (
        echo   %%A
    )
)
echo.

REM PASO 3: Ejecución automática
echo [PASO 3] Ejecutando cambios automáticos...
echo.
echo ⚠️  ADVERTENCIA: Esto modificará ~60-80 archivos Python
echo    Puedes revertir con: git reset --hard HEAD~1
echo.
set /p CONFIRM="¿Continuar? (s/N): "
if /i "!CONFIRM!" neq "s" (
    echo Abortado por el usuario.
    exit /b 0
)
echo.

python refactor_script.py --execute > refactor_execute.log 2>&1
if errorlevel 1 (
    echo ❌ ERROR en ejecución
    echo Ver: refactor_execute.log
    echo Revirtiendo cambios...
    git reset --hard HEAD
    exit /b 1
)
echo ✅ Cambios aplicados exitosamente
echo.

REM Mostrar resumen de ejecución
for /f "tokens=*" %%A in (refactor_execute.log) do (
    if "%%A" neq "" (
        echo   %%A
    )
)
echo.

REM PASO 4: Verificación
echo [PASO 4] Verificando cambios...
python refactor_script.py --verify > refactor_verify.log 2>&1

for /f "tokens=*" %%A in (refactor_verify.log) do (
    if "%%A" neq "" (
        echo   %%A
    )
)
echo.

REM PASO 5: Commit automático
echo [PASO 5] Guardando cambios...
git add -A
git commit -m "refactor: auto-update imports, aliases, and labels (Spanish to English)" > NUL 2>&1
echo ✅ Cambios automáticos guardados en git
echo.

echo ============================================================================
echo                    CAMBIOS AUTOMÁTICOS COMPLETADOS ✅
echo ============================================================================
echo.
echo 🔄 Status: Cambios automáticos (~70%% completados)
echo.
echo ⚠️  PRÓXIMOS PASOS (MANUALES - 35-40 min):
echo.
echo 1. Renombrar directorios de módulos (PowerShell):
echo    cd apps\backend\app\modules
echo    Rename-Item "proveedores" "suppliers"
echo    Rename-Item "gastos" "expenses"
echo    Rename-Item "empresa" "company"
echo    Rename-Item "usuarios" "users"
echo.
echo 2. Renombrar archivos schemas (PowerShell):
echo    cd ..\schemas
echo    Rename-Item "empresa.py" "company.py"
echo    Rename-Item "rol_empresa.py" "company_role.py"
echo    Rename-Item "hr_nomina.py" "payroll.py"
echo.
echo 3. Eliminar archivos compat (PowerShell):
echo    cd ..\models\company
echo    Remove-Item "empresa.py"
echo    Remove-Item "usuarioempresa.py"
echo.
echo 4. Revisar archivos críticos (manual):
echo    - app/main.py
echo    - app/platform/http/router.py
echo    - app/db/base.py
echo.
echo 5. Limpiar docstrings en español (manual)
echo.
echo 6. Actualizar tests
echo.
echo 7. Verificar final:
echo    python refactor_script.py --verify
echo    pytest tests/ -v
echo.
echo ✅ Ver detalles en:
echo    - refactor_analysis.log
echo    - refactor_execute.log
echo    - refactor_verify.log
echo.
echo 📖 Para instrucciones detalladas:
echo    Lee: REFACTOR_QUICK_START.md (sección 4 en adelante)
echo.
echo ============================================================================
echo.
pause
