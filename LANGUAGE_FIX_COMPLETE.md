# Language Configuration - Tenant-Based Implementation Complete

## Summary

El sistema de idiomas ahora usa la configuración de cada empresa (tenant) en lugar de un idioma global por defecto.

## What Changed

### Before
```
defaultLang = "es" → Todos los usuarios veían español
```

### Now
```
Idioma por defecto: "en"
    ↓
CompanyConfigProvider carga config del tenant
    ↓
useTenantLanguage() obtiene locale del tenant (ej: "es")
    ↓
i18n cambia automáticamente al idioma del tenant
    ↓
Resultado: Cada empresa ve su idioma configurado
```

## Files Created/Modified

### 1. New Files Created

**`apps/tenant/src/i18n/useTenantLanguage.ts`**
- Hook que aplica automáticamente el idioma del tenant
- Normaliza el locale a "es" o "en"
- Se ejecuta cuando CompanyConfigContext carga

**`apps/tenant/src/app/AppWithTenantLanguage.tsx`**
- Componente wrapper que envuelve la app
- Ejecuta `useTenantLanguage()` hook
- Necesario para que el idioma se aplique antes de renderizar

### 2. Modified Files

**`apps/tenant/src/main.tsx`**
- Reordenó providers: `I18nProvider` antes de `CompanyProvider`
- Agregó `AppWithTenantLanguage` wrapper
- Cambió `defaultLang` de "es" a "en"

**`apps/tenant/src/app/App.tsx`**
- Cambió mensaje de carga de "Cargando..." a "Loading..."

**`apps/tenant/src/i18n/I18nProvider.tsx`**
- Cambió `defaultLang` de "es" a "en"

**`apps/tenant/src/i18n/index.ts`**
- Sin cambios (ya tenía `normalizeLang()`)

## How It Works

### Component Tree
```
AuthProvider (usuario autenticado)
    ↓
I18nProvider (idioma inicial: "en")
    ↓
CompanyProvider (carga config de empresa)
    ↓
AppWithTenantLanguage (aplica idioma del tenant)
    ├─ useEffect que obtiene settings.locale
    ├─ Normaliza a "es" o "en"
    └─ Cambia i18n.language
        ↓
ToastProvider, App (usan el idioma correcto)
```

### Data Flow

```json
// Backend retorna:
{
  "settings": {
    "locale": "es"  // ← Se obtiene de aquí
  }
}

// useTenantLanguage() normaliza:
"es" → "es"
"es-ES" → "es"
"en-US" → "en"

// i18n cambia automáticamente:
i18n.changeLanguage("es")

// Toda la UI se re-renderiza en español
```

## Testing

### Scenario 1: Empresa con locale "es"
```bash
1. Loguear en empresa "Variedades Lilit"
2. Verificar que locale en BD es "es"
3. Debe mostrar UI en español
```

### Scenario 2: Empresa con locale "en"
```bash
1. Loguear en empresa "Acme Corp"
2. Verificar que locale en BD es "en"
3. Debe mostrar UI en inglés
```

### Scenario 3: Cambiar locale de empresa
```bash
1. Admin cambia locale en Configuración → es → en
2. Usuario ve UI en inglés inmediatamente (en nuevo ciclo de carga)
3. O refrescando página (F5)
```

## Fallback Behavior

| Escenario | Resultado |
|-----------|-----------|
| Tenant locale = "es" | UI en español ✓ |
| Tenant locale = "en" | UI en inglés ✓ |
| Tenant locale = null | UI en inglés (defecto) ✓ |
| Tenant locale = "xyz" | UI en inglés (normaliza a "en") ✓ |
| localStorage tiene "es" | Sobrescrito por tenant locale ✓ |

## localStorage Precedence

1. **Tenant locale** (más alta prioridad) ← Aquí está ahora
2. localStorage (si tenant locale vacío)
3. Browser language preference
4. Fallback "en" (más baja prioridad)

## Performance

- `useTenantLanguage()` se ejecuta 1 vez al cargar tenant
- No genera renders innecesarios (guard de igualdad)
- Cambios asincronos sin bloquear UI

## Edge Cases Handled

✅ Usuario sin tenant cargado aún → Usa "en" por defecto
✅ Cambio de locale mientras app cargada → Requiere refresh (por diseño)
✅ Locale inválido en BD → Se normaliza a "en"
✅ Tenant locale null/undefined → Usa "en"
✅ i18n change error → Loguea warning pero no crashea

## Backwards Compatibility

- ✅ Componentes existentes siguen usando `useTranslation()`
- ✅ No rompe rutas existentes
- ✅ Respeta localStorage de usuarios anteriores (si aplica)

## Known Limitations

❌ Cambio de locale requiere refrescar página (F5)
   → Solución futura: agregar selector de idioma en UI

❌ No hay persistencia de preferencia de usuario
   → Solución futura: agregar tabla `user_language_preferences`

## Next Steps (Optional)

### Agregar selector de idioma en UI
```tsx
function LanguageSelector() {
  const { setLang } = useI18n()
  return (
    <select onChange={(e) => setLang(e.target.value)}>
      <option value="en">English</option>
      <option value="es">Español</option>
    </select>
  )
}
```

### Persistir preferencia del usuario
```sql
CREATE TABLE user_preferences (
  user_id UUID PRIMARY KEY,
  preferred_language VARCHAR(10),
  FOREIGN KEY (user_id) REFERENCES auth_users(id)
)
```

### Agregar más idiomas
```typescript
export const SUPPORTED_LANGS = ['en', 'es', 'pt', 'fr'] as const
// + Crear archivos de traducción en i18n/locales/pt.json, etc.
```

## Deployment Checklist

- [x] Hook `useTenantLanguage.ts` creado
- [x] Componente `AppWithTenantLanguage.tsx` creado
- [x] `main.tsx` actualizado con nuevos providers
- [x] Documentación creada
- [x] Sin breaking changes
- [x] Backwards compatible

## Files Summary

```
Created:
  - apps/tenant/src/i18n/useTenantLanguage.ts (34 líneas)
  - apps/tenant/src/app/AppWithTenantLanguage.tsx (15 líneas)

Modified:
  - apps/tenant/src/main.tsx (1 import + 6 líneas de reorden)
  - apps/tenant/src/app/App.tsx (1 línea)
  - apps/tenant/src/i18n/I18nProvider.tsx (1 línea)

Total Changes: ~50 líneas de código, 0 breaking changes
```

---

**Status**: ✅ IMPLEMENTADO Y LISTO
**Fecha**: 2025-01-22
**Probado en**: desarrollo local
