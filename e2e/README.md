# Tests E2E con Playwright

## Instalación

```bash
npm init -y  # Solo si no existe package.json en la raíz
npm install -D @playwright/test
npx playwright install
```

## Comandos

```bash
# Ejecutar todos los tests
npx playwright test

# Ejecutar tests en un navegador específico
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Ejecutar tests con UI interactiva
npx playwright test --ui

# Ejecutar un archivo específico
npx playwright test e2e/smoke.spec.ts

# Ver reporte HTML
npx playwright show-report

# Ejecutar en modo headed (ver navegador)
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

## Variables de entorno

- `BASE_URL`: URL base de la aplicación (default: `http://localhost:5173`)
- `CI`: Modo CI/CD (aumenta retries, reduce workers)

```bash
# Ejemplo con URL personalizada
BASE_URL=http://localhost:3000 npx playwright test
```

## Estructura de tests

- `smoke.spec.ts` - Tests básicos de carga de la aplicación
- `auth.spec.ts` - Tests de flujo de autenticación
- `navigation.spec.ts` - Tests de navegación

## Añadir a package.json (opcional)

Si creas un package.json en la raíz:

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:report": "playwright show-report"
  }
}
```
