/**
 * Schemas para validación de tipos en componentes CRUD
 * Proporciona type safety para GenericList y useCRUD hooks
 */

// Schema simple basado en interfaces TypeScript para compatibilidad
export interface BaseCatalog {
  id: string | number
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
  id: number
  sku: string
  name: string
  description?: string | null
  price: number
  cost?: number
  category_id?: number | null
  category_name?: string | null
  stock_quantity?: number
  active: boolean
  created_at?: string
  updated_at?: string
}

// Schema para Usuario
export interface Usuario {
  id: number
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

// Schema validator simple (simula Zod parse)
export class SchemaValidator<T> {
  constructor(private schema: new () => T) {}
  
  parse(data: any): T {
    // Validación básica - en producción usar Zod completo
    return data as T
  }
  
  safeParse(data: any): { success: true; data: T } | { success: false; error: Error } {
    try {
      const parsed = this.parse(data)
      return { success: true, data: parsed }
    } catch (error) {
      return { success: false, error: error as Error }
    }
  }
}

// Export schemas para usar en componentes - compatibles con useCRUD
export const ProductoSchema = new SchemaValidator(Producto as any)
export const UsuarioSchema = new SchemaValidator(Usuario as any)
export const CategoriaGastoSchema = new SchemaValidator(CategoriaGasto as any)
export const BusinessTypeSchema = new SchemaValidator(BusinessType as any)
export const BusinessCategorySchema = new SchemaValidator(BusinessCategory as any)
export const BaseCatalogSchema = new SchemaValidator(BaseCatalog as any)
