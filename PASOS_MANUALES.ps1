# ============================================================================
#                REFACTORING BACKEND - PASOS MANUALES
#                     PowerShell Script
# ============================================================================
# Ejecuta los cambios manuales después del script automático
# ============================================================================

# Colors for output
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Red = [System.ConsoleColor]::Red
$Cyan = [System.ConsoleColor]::Cyan

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 80
    Write-Host $Text -ForegroundColor $Cyan
    Write-Host "=" * 80
}

function Write-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor $Yellow
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor $Red
}

function Pause-Execution {
    param([string]$Message = "Presiona Enter para continuar...")
    Read-Host $Message
}

# ============================================================================
# INICIO
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗"
Write-Host "║       REFACTORING BACKEND - PASOS MANUALES                    ║"
Write-Host "║       Renombrar módulos, esquemas y eliminar legacy files     ║"
Write-Host "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""

$BaseDir = "c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app"

# ============================================================================
# PASO 1: RENOMBRAR MÓDULOS
# ============================================================================

Write-Header "PASO 1: RENOMBRAR DIRECTORIOS DE MÓDULOS"

$ModulesDir = "$BaseDir\modules"
Write-Host "Cambiando a directorio: $ModulesDir"

if (-Not (Test-Path $ModulesDir)) {
    Write-Error-Custom "Directorio no encontrado: $ModulesDir"
    exit 1
}

cd $ModulesDir
Write-Success "Ubicación actual: $(Get-Location)"
Write-Host ""
Write-Host "Directorios a renombrar:"
Write-Host "  proveedores → suppliers"
Write-Host "  gastos → expenses"
Write-Host "  empresa → company"
Write-Host "  usuarios → users"
Write-Host ""

$Mappings = @{
    "proveedores" = "suppliers"
    "gastos" = "expenses"
    "empresa" = "company"
    "usuarios" = "users"
}

foreach ($Old in $Mappings.Keys) {
    $New = $Mappings[$Old]

    if (Test-Path $Old) {
        Write-Host "Renombrando: $Old → $New"
        try {
            Rename-Item -Path $Old -NewName $New -ErrorAction Stop
            Write-Success "Renombrado: $Old → $New"
        }
        catch {
            Write-Error-Custom "Error renombrando $Old : $_"
        }
    }
    else {
        Write-Warning "No existe: $Old (ya renombrado?)"
    }
    Write-Host ""
}

Write-Host "Directorios actuales en modules/:"
Get-ChildItem -Directory | Where-Object {$_.Name -notmatch "^_|^__"} | ForEach-Object {
    Write-Host "  📁 $($_.Name)"
}

Pause-Execution

# ============================================================================
# PASO 2: RENOMBRAR ARCHIVOS SCHEMAS
# ============================================================================

Write-Header "PASO 2: RENOMBRAR ARCHIVOS SCHEMAS"

$SchemasDir = "$BaseDir\schemas"
Write-Host "Cambiando a directorio: $SchemasDir"

if (-Not (Test-Path $SchemasDir)) {
    Write-Error-Custom "Directorio no encontrado: $SchemasDir"
    exit 1
}

cd $SchemasDir
Write-Success "Ubicación actual: $(Get-Location)"
Write-Host ""
Write-Host "Archivos a renombrar:"
Write-Host "  empresa.py → company.py"
Write-Host "  rol_empresa.py → company_role.py"
Write-Host "  hr_nomina.py → payroll.py"
Write-Host "  configuracionempresasinicial.py → company_initial_config.py"
Write-Host ""

$FileMappings = @{
    "empresa.py" = "company.py"
    "rol_empresa.py" = "company_role.py"
    "hr_nomina.py" = "payroll.py"
    "configuracionempresasinicial.py" = "company_initial_config.py"
}

foreach ($Old in $FileMappings.Keys) {
    $New = $FileMappings[$Old]

    if (Test-Path $Old) {
        Write-Host "Renombrando: $Old → $New"
        try {
            Rename-Item -Path $Old -NewName $New -ErrorAction Stop
            Write-Success "Renombrado: $Old → $New"
        }
        catch {
            Write-Error-Custom "Error renombrando $Old : $_"
        }
    }
    else {
        Write-Warning "No existe: $Old (ya renombrado?)"
    }
    Write-Host ""
}

Write-Host "Archivos schema actuales (primeros 20):"
Get-ChildItem -Filter "*.py" | Select-Object -First 20 | ForEach-Object {
    Write-Host "  📄 $($_.Name)"
}

Pause-Execution

# ============================================================================
# PASO 3: ELIMINAR ARCHIVOS COMPAT/LEGACY
# ============================================================================

Write-Header "PASO 3: ELIMINAR ARCHIVOS LEGACY (COMPAT)"

$CompanyDir = "$BaseDir\models\company"
Write-Host "Cambiando a directorio: $CompanyDir"

if (-Not (Test-Path $CompanyDir)) {
    Write-Error-Custom "Directorio no encontrado: $CompanyDir"
    exit 1
}

cd $CompanyDir
Write-Success "Ubicación actual: $(Get-Location)"
Write-Host ""

$LegacyFiles = @("empresa.py", "usuarioempresa.py")

foreach ($File in $LegacyFiles) {
    if (Test-Path $File) {
        Write-Warning "Archivo legacy encontrado: $File"
        Write-Host "Este es un archivo de compatibilidad que debe ser eliminado."
        Write-Host ""

        # Verificar contenido
        Write-Host "Contenido del archivo:"
        Get-Content $File | ForEach-Object { Write-Host "  $_" }
        Write-Host ""

        $Confirm = Read-Host "¿Eliminar $File ? (s/N)"

        if ($Confirm -eq "s" -or $Confirm -eq "S") {
            try {
                Remove-Item $File -Force -ErrorAction Stop
                Write-Success "Eliminado: $File"
            }
            catch {
                Write-Error-Custom "Error eliminando $File : $_"
            }
        }
        else {
            Write-Warning "No eliminado: $File"
        }
    }
    else {
        Write-Host "✓ No existe (OK): $File"
    }
    Write-Host ""
}

Write-Host "Archivos en company/ después de eliminación:"
Get-ChildItem -Filter "*.py" | Where-Object {$_.Name -notmatch "^__"} | ForEach-Object {
    Write-Host "  📄 $($_.Name)"
}

Pause-Execution

# ============================================================================
# PASO 4: GIT COMMIT
# ============================================================================

Write-Header "PASO 4: GUARDAR CAMBIOS MANUALES EN GIT"

cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto

Write-Host "Verificando status git..."
$Status = git status --porcelain

if ($Status) {
    Write-Host "Cambios detectados:"
    $Status | ForEach-Object { Write-Host "  $_" }
    Write-Host ""

    $Commit = Read-Host "¿Hacer commit de estos cambios? (s/N)"

    if ($Commit -eq "s" -or $Commit -eq "S") {
        git add -A
        git commit -m "refactor: rename modules/schemas and delete legacy files"
        Write-Success "Cambios guardados en git"
    }
    else {
        Write-Warning "Cambios no guardados"
    }
}
else {
    Write-Host "✓ Sin cambios pendientes"
}

Pause-Execution

# ============================================================================
# RESUMEN
# ============================================================================

Write-Header "RESUMEN DE PASOS MANUALES"

Write-Host ""
Write-Host "✅ Pasos completados:"
Write-Host ""
Write-Host "  [✓] Módulos renombrados:"
Write-Host "      proveedores → suppliers"
Write-Host "      gastos → expenses"
Write-Host "      empresa → company"
Write-Host "      usuarios → users"
Write-Host ""
Write-Host "  [✓] Esquemas renombrados:"
Write-Host "      empresa.py → company.py"
Write-Host "      rol_empresa.py → company_role.py"
Write-Host "      hr_nomina.py → payroll.py"
Write-Host "      configuracionempresasinicial.py → company_initial_config.py"
Write-Host ""
Write-Host "  [✓] Archivos legacy eliminados (si existían)"
Write-Host ""
Write-Host "⚠️  PRÓXIMOS PASOS (MANUALES - 20 min):"
Write-Host ""
Write-Host "  1. Revisar archivos críticos:"
Write-Host "     - app/main.py"
Write-Host "     - app/platform/http/router.py"
Write-Host "     - app/db/base.py"
Write-Host "     Buscar referencias a módulos/esquemas antiguos"
Write-Host ""
Write-Host "  2. Limpiar docstrings en español (15 min):"
Write-Host "     Archivos: app/schemas/*.py"
Write-Host "              app/modules/*/interface/http/tenant.py"
Write-Host "              app/models/*/docstrings"
Write-Host ""
Write-Host "  3. Actualizar imports en tests"
Write-Host ""
Write-Host "  4. Verificación final:"
Write-Host "     python refactor_script.py --verify"
Write-Host "     pytest tests/ -v"
Write-Host ""
Write-Host "  5. Commit final y push:"
Write-Host "     git add -A"
Write-Host "     git commit -m 'refactor: final cleanup'"
Write-Host "     git push origin refactor/spanish-to-english"
Write-Host ""
Write-Host "📖 Ver detalles en: REFACTOR_QUICK_START.md"
Write-Host ""

Write-Host "¿Continuar con pasos manuales restantes? (detalles en REFACTOR_QUICK_START.md)"
Pause-Execution "Presiona Enter para cerrar este script..."

Write-Host ""
Write-Host "✨ ¡Script completado!"
Write-Host ""
