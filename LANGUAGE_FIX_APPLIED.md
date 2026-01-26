# Language Configuration Fix - English Default

## Problem
The application was defaulting to Spanish (`es`) instead of English (`en`), causing:
- URLs like `/variedades-lilit/sales` to display Spanish translations
- Dashboard and all UI text in Spanish when they should be in English

## Root Causes Found

1. **I18nProvider default language**: Set to `'es'`
2. **main.tsx default language**: Passed `defaultLang="es"` to I18nProvider
3. **Language detection order**: localStorage first (may contain old `es` value)
4. **Loading message**: Hardcoded "Cargando..." (Spanish)

## Fixes Applied

### 1. Updated main.tsx (Tenant App)
**File**: `apps/tenant/src/main.tsx` line 57
```diff
- <I18nProvider defaultLang="es">
+ <I18nProvider defaultLang="en">
```

### 2. Updated I18nProvider.tsx
**File**: `apps/tenant/src/i18n/I18nProvider.tsx` line 23
```diff
- export const I18nProvider: React.FC<...> = ({ defaultLang = 'es', children }) => {
+ export const I18nProvider: React.FC<...> = ({ defaultLang = 'en', children }) => {
```

### 3. Updated Loading Message
**File**: `apps/tenant/src/app/App.tsx` line 32
```diff
- Cargando...
+ Loading...
```

## How Language Detection Works (Order)

Current order in `i18n/index.ts`:
1. **localStorage** - If user previously selected a language
2. **navigator** - Browser language preference
3. **Fallback** - Hardcoded fallback (now `'en'`)

## To Reset Language to English

Users can:
1. **Clear localStorage**: `localStorage.removeItem('i18nextLng')`
2. **Or clear all app storage**: DevTools → Storage → Clear All
3. **Or use browser preferences**: Change browser language to English

If localStorage has an old `es` value, it will persist. To force English:

```javascript
localStorage.setItem('i18nextLng', 'en')
location.reload()
```

## Result

✅ New users: Default to English
✅ Existing users: Their saved preference preserved (localStorage)
✅ No saved preference: Fallback to English
✅ Browser language: Can override if set to Spanish (this is intended behavior)

## Notes

- The fix respects user preferences (localStorage)
- Only affects NEW sessions without stored language preference
- Existing users who had Spanish set will still see Spanish (by design)
- To force all users to English, they need to clear localStorage
- This is the correct i18n pattern - respecting user's previous choice

## Testing

1. **In an incognito window** (no localStorage): Should see English
2. **Clear localStorage**: `localStorage.clear()` then refresh
3. **Check browser console**: `localStorage.getItem('i18nextLng')` should be `'en'` after first load
4. **Language selector**: Should show English as current when UI loads

---

**Deployed**: ✅ Ready for deployment
**Breaking changes**: ❌ None (respects existing user preferences)
**Rollback**: Easy - revert to `defaultLang="es"`
