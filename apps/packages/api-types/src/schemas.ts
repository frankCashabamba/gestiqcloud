/**
 * Schemas para validación de tipos en componentes CRUD
 * Proporciona type safety para GenericList y useCRUD hooks
 */

// Schema simple basado en interfaces TypeScript para compatibilidad
export interface BaseCatalog {
  id: string  // UUID del backend
  tenant_id?: string
  code?: string | null
  name: string
  description?: string | null
  is_active: boolean
  created_at?: string
  updated_at?: string
}

// Schema para Producto
export interface Producto {
  id: string  // UUID del backend
  sku: string
  name: string
  description?: string | null
  price: number
  cost?: number
  category_id?: string | null  // UUID del backend
  category_name?: string | null
  stock_quantity?: number
  active: boolean
  created_at?: string
  updated_at?: string
}

// Schema para Usuario
export interface Usuario {
  id: string  // UUID del backend
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  roles?: string[]
  created_at?: string
  last_login?: string
}

// Schema para Categoría de Gasto
export interface CategoriaGasto extends BaseCatalog {
  // Campos específicos si los hay
}

// Schema para BusinessType
export interface BusinessType extends BaseCatalog {
  id: string
}

// Schema para BusinessCategory
export interface BusinessCategory extends BaseCatalog {
  id: string
}

// Schema genérico para paginated response
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}
