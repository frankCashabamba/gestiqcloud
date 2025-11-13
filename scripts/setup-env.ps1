# PowerShell script to setup .env file for development

$envFile = ".env"
$envExampleFile = ".env.example"

Write-Host "GestiQCloud Environment Setup" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $envFile) {
    Write-Host "WARNING: El archivo .env ya existe." -ForegroundColor Yellow
    $response = Read-Host "Deseas sobrescribirlo? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Setup cancelado." -ForegroundColor Red
        exit 0
    }
}

if (-not (Test-Path $envExampleFile)) {
    Write-Host "ERROR: No se encuentra $envExampleFile" -ForegroundColor Red
    exit 1
}

Write-Host "Copiando $envExampleFile a $envFile..." -ForegroundColor Green
Copy-Item $envExampleFile $envFile

Write-Host ""
Write-Host "Archivo .env creado exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANTE: Edita el archivo .env y configura:" -ForegroundColor Yellow
Write-Host "   - EMAIL_HOST_PASSWORD (tu password de Mailtrap)" -ForegroundColor White
Write-Host "   - JWT_SECRET_KEY (para produccion usa uno seguro)" -ForegroundColor White
Write-Host ""
Write-Host "Para editar: code .env" -ForegroundColor Cyan
Write-Host ""
Write-Host "Luego ejecuta: docker compose up --build tenant admin backend" -ForegroundColor Green
Write-Host ""
