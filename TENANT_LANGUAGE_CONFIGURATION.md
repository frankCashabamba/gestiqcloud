# Tenant Language Configuration System

## Overview

El aplicativo ahora usa automáticamente el idioma configurado en la empresa (tenant), en lugar de un idioma global.

## Architecture

### Component Hierarchy
```
EnvProvider
  └─ BrowserRouter
      └─ AuthProvider
          └─ I18nProvider (defaultLang="en")
              └─ CompanyProvider (carga config del tenant)
                  └─ AppWithTenantLanguage (aplica idioma del tenant)
                      └─ ToastProvider
                          └─ App (rutas y módulos)
```

### Flujo de Carga de Idioma

1. **AuthProvider**: Usuario se autentica
2. **I18nProvider**: Inicializa i18n con idioma por defecto "en"
3. **CompanyProvider**: Carga configuración de la empresa (tenant)
   - Obtiene `settings.locale` (ej: "es", "en-US", etc.)
4. **AppWithTenantLanguage**: Hook `useTenantLanguage()` ejecuta
   - Normaliza el locale del tenant
   - Cambia automáticamente el idioma de i18n
   - Todos los componentes se re-renderizar con el nuevo idioma

### Files Involved

```
apps/tenant/src/
├── main.tsx
│   └─ Envoltura estructural con AppWithTenantLanguage
├── app/
│   └─ AppWithTenantLanguage.tsx (componente wrapper)
├── i18n/
│   ├─ index.ts (normalizeLang helper)
│   ├─ I18nProvider.tsx (proveedor global)
│   └─ useTenantLanguage.ts (hook que aplica idioma del tenant)
└── contexts/
    └─ CompanyConfigContext.tsx (carga config del tenant)
```

## Usage

### Para desarrolladores

**En componentes que necesitan traducción:**

```tsx
import { useTranslation } from 'react-i18next'

function MyComponent() {
  const { t } = useTranslation()
  return <div>{t('sales.total')}</div>
}
```

**Para obtener el idioma actual:**

```tsx
import i18n from '../i18n'
console.log(i18n.language) // 'es' o 'en'
```

### Para administradores/usuarios

**Cambiar idioma de una empresa:**
1. Ir a Configuración → Empresa
2. Cambiar "Locale" a:
   - `en` o `en-US` para Inglés
   - `es` o `es-ES` para Español
3. Guardar
4. Refrescar navegador

El cambio se aplicará automáticamente a todos los usuarios de esa empresa.

## Language Detection Flow

```
┌─────────────────────────────────────┐
│ CompanyConfigContext carga config   │
│ Obtiene: settings.locale = "es"     │
└────────────────────┬────────────────┘
                     │
                     ▼
┌─────────────────────────────────────┐
│ useTenantLanguage() hook ejecuta   │
│ normalizeLang("es") → "es"         │
└────────────────────┬────────────────┘
                     │
                     ▼
┌─────────────────────────────────────┐
│ i18n.changeLanguage("es")           │
│ Todos los componentes usan "es"     │
└─────────────────────────────────────┘
```

## Fallback Behavior

| Situación | Idioma Usado |
|-----------|-------------|
| Tenant tiene `locale` configurado | Usa locale del tenant |
| Tenant sin locale (null/empty) | Usa defecto del provider ("en") |
| Idioma inválido (ej: "xx") | Se normaliza a "en" |
| localStorage tiene idioma antiguo | Puede ser sobrescrito por tenant |

## Normalización de Locales

La función `normalizeLang()` acepta:
- `"es"`, `"ES"` → `"es"`
- `"es-ES"`, `"es_ES"` → `"es"`
- `"es-MX"`, `"es_AR"` → `"es"`
- `"en"`, `"EN"` → `"en"`
- `"en-US"`, `"en-GB"` → `"en"`
- Otros → `"en"` (fallback)

## localStorage Behavior

El i18next mantiene el idioma en localStorage bajo la clave `i18nextLng`.

**Precedencia:**
1. Idioma del tenant (más alta)
2. localStorage
3. Preferencia del navegador
4. Fallback por defecto (más baja)

**Para limpiar localStorage:**
```javascript
localStorage.removeItem('i18nextLng')
location.reload()
```

## Testing

### En desarrollo:

```bash
# Simular cambio de empresa
1. Loguear en empresa A con locale "es"
2. Verificar UI en español
3. Cambiar a empresa B con locale "en"
4. Verificar UI se actualiza a inglés automáticamente
```

### En código:
```tsx
import { useCompanyConfig } from '../contexts/CompanyConfigContext'

function TestComponent() {
  const { config } = useCompanyConfig()
  console.log('Tenant locale:', config?.settings?.locale)
  return null
}
```

## Troubleshooting

### "UI sigue en inglés aunque tenant es 'es'"

1. Verificar que `CompanyConfigContext` está cargando correctamente
2. Verificar que endpoint `/api/v1/company/settings/config` retorna `settings.locale`
3. Limpiar localStorage: `localStorage.clear()`
4. Forzar recarga: `Ctrl+Shift+R`

### "UI no cambia cuando cambio locale en tenant"

1. El cambio requiere refrescar la página (F5)
2. O abrir en incógnito sin cache
3. Verificar que CompanyProvider está dentro de I18nProvider

### "locale del tenant es null/undefined"

Verificar endpoint backend:
```bash
curl http://localhost:8082/api/v1/company/settings/config \
  -H "Authorization: Bearer {token}"
```

Debe retornar:
```json
{
  "settings": {
    "locale": "es",
    ...
  },
  ...
}
```

## Migration Guide (si cambiaste de sistema anterior)

**Antes:**
```tsx
<I18nProvider defaultLang="es">
  <App />
</I18nProvider>
```

**Ahora:**
```tsx
<I18nProvider defaultLang="en">
  <CompanyProvider>
    <AppWithTenantLanguage>
      <App />
    </AppWithTenantLanguage>
  </CompanyProvider>
</I18nProvider>
```

## Performance Notes

- `useTenantLanguage()` se ejecuta una sola vez al cargar tenant
- No genera loops infinitos (hay guard `if (i18n.language !== normalized)`)
- Los cambios se aplican de forma asincrónica sin bloquear render

## Future Enhancements

- [ ] Agregar selector de idioma en UI para que usuario pueda override
- [ ] Persistir preferencia del usuario en BD (separada de tenant)
- [ ] Soportar más idiomas (agregar a `SUPPORTED_LANGS`)
- [ ] RTL support para idiomas como árabe (requiere CSS)

---

**Status**: ✅ Implementado y listo para producción
**Última actualización**: 2025-01-22
