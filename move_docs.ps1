# Script para mover documentación a _deprecated_docs
$patterns = @(
    'RESUMEN_*.md', 'RESUMEN_*.txt',
    'OFFLINE_*.md', 'OFFLINE_*.txt',
    'TRADUCCION_*.md',
    'ANALISIS_*.md',
    'HARDCODEOS_*.md',
    'IMPLEMENTACION_*.md', 'IMPLEMENTACION_*.txt',
    'QUICK_START_*.md',
    'QUICKSTART_*.md',
    'PLAN_REMEDIACION_*.md',
    'TRACKING_*.md',
    'CHECKLIST_*.md',
    'CODIGOS_*.md',
    'DEVELOPMENT_*.md',
    'ENTREGA_*.txt',
    'ARCHIVOS_*.md', 'ARCHIVOS_*.txt',
    'CAMBIOS_*.md', 'CAMBIOS_*.txt',
    'FRONTEND_*.md',
    'DELIVERABLES_*.md',
    'API_*.md',
    'BACKEND_*.md',
    'MIGRATION_*.md',
    'ONBOARDING_*.md',
    'ENV_*.md',
    'desarrollo*.md',
    'documento*.md',
    'TRANSLATION_*.md',
    'TESTING_*.md',
    'VERIFICATION_*.md',
    'VERIFICACION_*.md',
    'TODO_*.md',
    'INDEX_*.md',
    'PROGRESO.md',
    'README_*.md',
    'LISTO_*.txt',
    'GIT_*.txt'
)

foreach ($pattern in $patterns) {
    Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Move-Item -Destination '_deprecated_docs' -Force -ErrorAction SilentlyContinue
}

Write-Host "Archivos movidos a _deprecated_docs/"
(ls '_deprecated_docs' | measure).Count | Write-Host "Total archivos:"
