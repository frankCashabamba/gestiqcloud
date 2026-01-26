# Internationalization (i18n) Guide

**Status:** ✅ Configured
**Supported Languages:** English (en), Spanish (es)
**Default Language:** English

---

## Overview

GestiqCloud supports multiple languages through:
- **Frontend (React):** `react-i18next` with browser language detection
- **Backend (Python):** Custom `t()` function with Accept-Language header support

---

## Frontend Usage

### Tenant App

```tsx
import { useTranslation } from '@/hooks/useTranslation'

function MyComponent() {
  const { t } = useTranslation()

  return (
    <div>
      <h1>{t('common.loading')}</h1>
      <button>{t('common.save')}</button>
      <p>{t('errors.required')}</p>
    </div>
  )
}
```

### Admin App

```tsx
import { useTranslation } from '@/hooks/useTranslation'

function AdminPage() {
  const { t } = useTranslation()

  return (
    <div>
      <h1>{t('countryPacks.title')}</h1>
      <button>{t('common.create')}</button>
    </div>
  )
}
```

### Interpolation

```tsx
// With variables
t('settings.modulesActive', { active: 5, total: 10 })
// Output: "5 of 10 active modules"

// In Spanish: "5 de 10 módulos activos"
```

### Language Selector

Add to your layout:

```tsx
import { LanguageSelector } from '@/components/LanguageSelector'

function Header() {
  return (
    <header>
      <LanguageSelector />
    </header>
  )
}
```

---

## Backend Usage

### Basic Translation

```python
from app.i18n import t

# Simple translation
message = t("errors.notFound", lang="es")  # "No encontrado"

# With interpolation
message = t("errors.itemNotFound", lang="en", item="Product")  # "Product not found"
```

### In HTTP Handlers

```python
from fastapi import Request, HTTPException
from app.i18n import t

@router.get("/items/{id}")
async def get_item(id: str, request: Request):
    lang = getattr(request.state, "lang", "en")

    item = db.get(id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=t("errors.itemNotFound", lang, item="Item")
        )
    return item
```

### Enable Middleware

Add to `main.py`:

```python
from app.i18n.middleware import I18nMiddleware

app.add_middleware(I18nMiddleware)
```

---

## Translation Files

### Frontend

| App | Location |
|-----|----------|
| Tenant | `apps/tenant/src/i18n/locales/{lang}.json` |
| Admin | `apps/admin/src/i18n/locales/{lang}.json` |

### Backend

| Location |
|----------|
| `apps/backend/app/i18n/locales/{lang}.json` |

---

## Adding a New Language

### 1. Frontend

Create `apps/tenant/src/i18n/locales/{lang}.json`:

```json
{
  "common": {
    "loading": "Chargement...",
    "save": "Enregistrer"
  }
}
```

Update `apps/tenant/src/i18n/index.ts`:

```typescript
import fr from './locales/fr.json'

const resources = {
  en: { translation: en },
  es: { translation: es },
  fr: { translation: fr },  // Add new language
}
```

Update `LanguageSelector.tsx`:

```typescript
const languages = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },  // Add new language
]
```

### 2. Backend

Create `apps/backend/app/i18n/locales/{lang}.json`:

```json
{
  "errors": {
    "notFound": "Non trouvé"
  }
}
```

No code changes needed - files are auto-loaded.

---

## Best Practices

### Keys

- Use **dot notation** for nested keys: `module.section.key`
- Use **camelCase** for key names: `errorLoading` not `error_loading`
- Group by feature/module: `webhooks.errors.loading`

### Translations

- Keep translations **short and clear**
- Use **interpolation** for dynamic values: `{count} items` not hardcoded
- Provide **context** in key names: `deleteConfirm` not just `confirm`

### Testing

```tsx
// Mock i18n in tests
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() }
  })
}))
```

---

## Translation Key Reference

### Common Keys (Frontend)

| Key | English | Spanish |
|-----|---------|---------|
| `common.loading` | Loading... | Cargando... |
| `common.save` | Save | Guardar |
| `common.cancel` | Cancel | Cancelar |
| `common.delete` | Delete | Eliminar |
| `common.edit` | Edit | Editar |
| `common.create` | Create | Crear |
| `common.active` | Active | Activo |
| `common.inactive` | Inactive | Inactivo |

### Error Keys (Backend)

| Key | English | Spanish |
|-----|---------|---------|
| `errors.notFound` | Not found | No encontrado |
| `errors.tokenExpired` | Token expired | Token expirado |
| `errors.tokenInvalid` | Invalid token | Token inválido |

---

## Migration from Hardcoded Strings

Before:
```tsx
<div>Cargando...</div>
```

After:
```tsx
const { t } = useTranslation()
<div>{t('common.loading')}</div>
```

Backend before:
```python
raise HTTPException(status_code=404, detail="No encontrado")
```

Backend after:
```python
raise HTTPException(status_code=404, detail=t("errors.notFound", lang))
```
