# API Centralization Pattern

## Overview
This document describes the standard pattern for centralizing hardcoded API endpoints in GestiCloud. The pattern eliminates scattered `fetch()` calls and hardcoded URL strings by consolidating them into dedicated API modules.

## Pattern Structure

### 1. Create Centralized API Module
**File**: `modules/{module}/apis/{module}Api.ts`

```typescript
// Example: productsApi.ts
import { apiFetch } from '../../lib/http'

// Step 1: Define ENDPOINTS constant
const ENDPOINTS = {
  products: {
    list: '/api/v1/tenant/products',
    get: (id: string) => `/api/v1/tenant/products/${id}`,
    create: '/api/v1/tenant/products',
    // ... all endpoints
  },
  categories: {
    list: '/api/v1/tenant/products/product-categories',
    create: '/api/v1/tenant/products/product-categories',
    delete: (id: string) => `/api/v1/tenant/products/product-categories/${id}`,
  },
} as const

// Step 2: Export types
export type Producto = {
  id: string
  name: string
  // ... properties
}

export type Categoria = {
  id: string
  name: string
}

// Step 3: Implement functions using ENDPOINTS
export async function listProductos(): Promise<Producto[]> {
  const res = await apiFetch<any>(ENDPOINTS.products.list)
  // ... normalization logic
  return products
}

export async function createProducto(data: Partial<Producto>): Promise<Producto> {
  return apiFetch<Producto>(ENDPOINTS.products.create, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

// Category functions
export async function listCategorias(): Promise<Categoria[]> {
  const data = await apiFetch<Categoria[]>(ENDPOINTS.categories.list)
  return Array.isArray(data) ? data : []
}
```

### 2. Update Existing services.ts for Backward Compatibility
**File**: `modules/{module}/services.ts`

```typescript
// DEPRECATED: Use {module}Api instead
// This file is kept for backward compatibility only
export * from './{module}Api'
```

### 3. Update Components
**Before**:
```typescript
// ❌ Hardcoded endpoint
const data = await apiFetch('/api/v1/tenant/products/product-categories')
```

**After**:
```typescript
// ✅ Using centralized API
import { listCategorias } from './productsApi'
const data = await listCategorias()
```

## Benefits

1. **Single Source of Truth**: All endpoints in one place
2. **Easy to Update**: Change backend endpoint in one location
3. **Type Safety**: All functions are properly typed
4. **Maintainability**: Clear API contract for the module
5. **Backward Compatibility**: Old imports still work via re-exports
6. **Testability**: Easy to mock API functions in tests

## Implementation Checklist

- [ ] Create `{module}Api.ts` with ENDPOINTS constant
- [ ] Define all types (request/response)
- [ ] Implement all functions using ENDPOINTS
- [ ] Add proper error handling
- [ ] Update components to use new API
- [ ] Convert `services.ts` to re-export from `{module}Api`
- [ ] Verify no hardcoded endpoints remain in components
- [ ] Test all functionality

## Example Modules

### ✅ Completed
- **Productos/Categorías**: `productsApi.ts`
- **Importador**: `importsApi.ts`, `columnMappingApi.ts`, `previewApi.ts`

### 🔄 In Progress
- None

### 📋 Planned
- Clientes (clientsApi.ts)
- Proveedores (suppliersApi.ts)
- Ventas (salesApi.ts)
- Compras (purchasesApi.ts)
- Gastos (expensesApi.ts)
- Finanzas (financeApi.ts)
- RRHH (hrApi.ts)
- Contabilidad (accountingApi.ts)
- Inventario (inventoryApi.ts)
- Producción (productionApi.ts)
- POS (posApi.ts)

## Guidelines

### ENDPOINTS Object
- Keep it flat and organized by resource
- Use functions for dynamic URLs with parameters
- Mark as `as const` for type inference

### Function Naming
- Use descriptive names: `listProductos`, `createProducto`, not `get`, `post`
- Match backend terminology for clarity
- Use consistent naming across modules

### Type Definitions
- Export all types from the API module
- Avoid duplicating types across files
- Include optional fields where they exist

### Error Handling
- Use `apiFetch` error handling (already configured)
- Don't add extra try-catch in API module
- Let components handle errors

### Normalization
- Handle different response formats (array vs. {items: []})
- Convert field names if needed
- Document transformation logic

## Migration Path

For each module (e.g., Clientes):
1. Identify all hardcoded endpoints
2. Create `clientsApi.ts` following pattern
3. Update components to import from API
4. Deprecate old `services.ts`
5. Verify tests pass
6. Commit with clear message

## Testing

Each API module should have a corresponding test file:
```typescript
// clientsApi.test.ts
import { listClientes, createCliente } from './clientsApi'
import * as http from '../../lib/http'

jest.mock('../../lib/http')

describe('clientsApi', () => {
  it('should fetch clients from correct endpoint', async () => {
    // ...
  })
})
```
