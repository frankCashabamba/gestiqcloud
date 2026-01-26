# 🚀 Quick Start - Frontend Development

**Fecha:** Enero 19, 2026  
**Versión:** 1.0

---

## 📋 Estructura del Proyecto

```
gestiqcloud/
├── apps/
│   ├── admin/           # Admin Panel (Angular-like)
│   │   └── src/
│   │       ├── pages/           # Páginas principales
│   │       ├── features/        # Componentes por feature
│   │       ├── services/        # API calls
│   │       ├── hooks/           # React hooks
│   │       ├── app/             # Routing
│   │       └── ...
│   ├── tenant/          # Frontend tenant (Módulos de negocio)
│   │   └── src/
│   │       ├── modules/         # 17 módulos de negocio
│   │       └── ...
│   ├── backend/         # API
│   └── packages/        # Shared components
├── FRONTEND_DEVELOPMENT_PLAN.md      # Plan completo
├── FRONTEND_COMPLETION_SUMMARY.md    # Resumen
└── TESTING_CHECKLIST.md              # Testing guide
```

---

## 🛠️ Instalación

### Requisitos
- Node.js 16+
- npm o yarn

### Setup
```bash
# Clonar repo
git clone https://github.com/frankCashabamba/gestiqcloud.git
cd gestiqcloud

# Instalar dependencias
npm install

# Instalar en admin específicamente
cd apps/admin
npm install
```

### Variables de Entorno
```bash
# apps/admin/.env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=GestiqCloud Admin
```

### Ejecutar
```bash
# Desde gestiqcloud root
npm run dev:admin

# O desde apps/admin
npm run dev
```

---

## 📁 Patrones y Convenciones

### Estructura de Feature

```
features/my-feature/
├── MyFeature.tsx          # Componente principal
├── MyFeatureList.tsx      # Sub-componentes
├── MyFeatureForm.tsx
├── styles.css
└── index.ts              # Exports
```

### Estructura de Servicio

```typescript
// services/my-feature.ts

export interface MyEntity {
  id: string;
  name: string;
  // ... otros campos
}

export async function getMyEntities(): Promise<MyEntity[]> {
  return apiClient.myFeature.list();
}

export async function getMyEntity(id: string): Promise<MyEntity> {
  return apiClient.myFeature.get(id);
}

// ... más funciones
```

### Estructura de Hook

```typescript
// hooks/useMyFeature.ts

export function useMyFeature() {
  const [data, setData] = useState<MyEntity[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  return { data, loading, error, refetch: fetchData };
}
```

---

## 🎨 Diseño Responsivo

### Breakpoints Estándar
```css
/* Mobile first */
/* 0px - 600px: Mobile */
/* 601px - 1024px: Tablet */
/* 1025px+: Desktop */

@media (min-width: 601px) { /* Tablet */ }
@media (min-width: 1025px) { /* Desktop */ }
```

### Grid Layout
```css
/* Desktop: 4 columnas */
grid-template-columns: repeat(4, 1fr);

/* Tablet: 2 columnas */
@media (max-width: 1024px) {
  grid-template-columns: repeat(2, 1fr);
}

/* Mobile: 1 columna */
@media (max-width: 600px) {
  grid-template-columns: 1fr;
}
```

---

## 🎯 Agregar Nueva Feature

### 1. Crear Servicio

```typescript
// services/my-feature.ts
export interface MyEntity { /* ... */ }

export async function getMyEntities() { /* ... */ }
export async function createMyEntity(data) { /* ... */ }
export async function updateMyEntity(id, data) { /* ... */ }
export async function deleteMyEntity(id) { /* ... */ }
```

### 2. Crear Hook

```typescript
// hooks/useMyFeature.ts
export function useMyFeature() {
  // Usar servicio, manejar estado, retornar datos
}
```

### 3. Crear Componentes

```typescript
// features/my-feature/MyFeature.tsx
export const MyFeature: React.FC = () => {
  const { data, loading, error } = useMyFeature();
  // JSX aquí
}
```

### 4. Crear Página (si es top-level)

```typescript
// pages/MyFeature.tsx
import { MyFeature } from '../features/my-feature/MyFeature';

export const MyFeaturePage: React.FC = () => {
  return <MyFeature />;
}
```

### 5. Agregar Ruta

```typescript
// app/App.tsx
import { MyFeaturePage } from '../pages/MyFeature';

// En Routes:
<Route path="my-feature" element={<MyFeaturePage />} />
```

### 6. Agregar Estilos

```css
/* features/my-feature/styles.css */
.my-feature {
  /* ... */
}
```

---

## 🔌 API Integration

### Client Centralizado

```typescript
// services/api.ts
export const apiClient = {
  myFeature: {
    list: () => GET('/my-feature'),
    get: (id) => GET(`/my-feature/${id}`),
    create: (data) => POST('/my-feature', data),
    update: (id, data) => PUT(`/my-feature/${id}`, data),
    delete: (id) => DELETE(`/my-feature/${id}`),
  },
};
```

### Usar en Servicios

```typescript
// services/my-feature.ts
import apiClient from './api';

export async function getMyEntities() {
  return apiClient.myFeature.list();
}
```

---

## 🎨 Colores y Estilos

### Paleta Estándar

```css
:root {
  --primary: #3b82f6;      /* Azul */
  --success: #10b981;      /* Verde */
  --warning: #f59e0b;      /* Ámbar */
  --danger: #ef4444;       /* Rojo */
  --info: #06b6d4;         /* Cian */

  --bg-light: #f9fafb;
  --bg-white: #ffffff;
  --border: #e5e7eb;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
}
```

### Componentes Comunes

```typescript
// Botón primario
<button className="btn btn--primary">Click</button>

// Card
<div className="card">
  <div className="card__header">Título</div>
  <div className="card__body">Contenido</div>
</div>

// Table
<table className="table">
  <thead className="table__head">
  <tbody className="table__body">
</table>
```

---

## 📊 Debugging

### React DevTools
```bash
# Instalar extensión en Chrome/Firefox
# Luego en DevTools > Components
```

### Redux DevTools (si se usa)
```bash
# Instalar extensión
# Luego en DevTools > Redux
```

### Console Logging
```typescript
// Buena práctica
console.log('Label:', value);
console.error('Error:', error);
console.warn('Warning:', warning);

// Evitar
console.log(anything); // Sin contexto
```

### Network Tab
```
DevTools > Network
- Revisar requests/responses
- Verificar status codes
- Revisar timing
```

---

## 🧪 Testing

### Unit Test (Vitest)
```typescript
import { describe, it, expect } from 'vitest';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    // test
  });
});
```

### E2E Test (Playwright)
```typescript
import { test, expect } from '@playwright/test';

test('user can navigate dashboard', async ({ page }) => {
  await page.goto('/admin/dashboard');
  // assertions
});
```

---

## 📝 Commits y Git

### Formato de Commit
```
feat: Agregar dashboard con KPIs
fix: Corregir bug en notificaciones
refactor: Reorganizar estructura de webhooks
docs: Actualizar readme
```

### Branch Naming
```
feature/dashboard-kpis
fix/notification-bug
docs/api-integration
```

---

## 🚀 Deploy

### Build
```bash
npm run build

# Output en: dist/
```

### Verificar Build
```bash
npm run preview
```

### Deploy (según tu setup)
```bash
# Vercel
vercel

# Netlify
netlify deploy

# Manual
scp -r dist/* user@server:/var/www/admin
```

---

## 🔍 Checklist Antes de Commit

- [ ] Código compila sin errores
- [ ] No hay console.log() de debug
- [ ] Tests pasan (si existen)
- [ ] Estilos responsive en mobile/tablet/desktop
- [ ] Comentarios de código si es complejo
- [ ] Commit message es descriptivo
- [ ] No hay archivos no deseados

---

## 📚 Recursos

### Documentación
- [React Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)

### Componentes
- [Headless UI](https://headlessui.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Recharts](https://recharts.org/)

### Tools
- [Prettier](https://prettier.io/) - Code formatter
- [ESLint](https://eslint.org/) - Linter
- [TypeScript](https://www.typescriptlang.org/) - Type safety

---

## 💡 Tips & Tricks

### Performance
```typescript
// ✅ Bueno
const data = useMemo(() => expensiveOperation(), [deps]);
const handler = useCallback(() => {...}, [deps]);

// ❌ Malo
const data = expensiveOperation(); // En cada render
const handler = () => {...}; // Nueva función cada render
```

### State Management
```typescript
// ✅ Bueno - Múltiples estados pequeños
const [name, setName] = useState('');
const [email, setEmail] = useState('');

// ⚠️ Considerar - Múltiples estados relacionados
const [formData, setFormData] = useState({ name: '', email: '' });
```

### Rendering
```typescript
// ✅ Bueno - Condicional simple
{loading && <Spinner />}
{error && <Error message={error.message} />}
{data && <List items={data} />}

// ❌ Malo
{loading === true ? <Spinner /> : null}
{!loading && !error && data ? <List items={data} /> : null}
```

---

## 🆘 Troubleshooting

### Build fails
```bash
# Limpiar cache
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Hot reload no funciona
```bash
# Reiniciar dev server
# Ctrl+C y npm run dev
```

### API calls fallan
```bash
# Revisar:
# 1. URL en .env
# 2. CORS headers en backend
# 3. Auth token en headers
# 4. Network tab en DevTools
```

---

**Última actualización:** Enero 19, 2026  
**Versión:** 1.0  
**Autor:** AI Assistant
