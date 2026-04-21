/**
 * Employee Department Types - Example using centralized types
 */

// Base types that would normally come from @packages/api-types
export type UUID = string
export type Timestamp = string

export interface BaseCatalog {
  id: UUID
  tenant_id?: UUID
  code?: string
  name: string
  description?: string
  is_active: boolean
  created_at: Timestamp
  updated_at: Timestamp
}

export interface CatalogCreateRequest {
  code?: string
  name: string
  description?: string
  is_active?: boolean
}

export interface CatalogUpdateRequest {
  code?: string
  name?: string
  description?: string
  is_active?: boolean
}

export interface CatalogFilters {
  page?: number
  per_page?: number
  search?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Employee Department extends BaseCatalog with tenant isolation
export interface EmployeeDepartment extends BaseCatalog {
  tenant_id: UUID
}

// Request types for API operations
export type EmployeeDepartmentCreate = CatalogCreateRequest & {
  // Additional fields specific to EmployeeDepartment can go here
}

export type EmployeeDepartmentUpdate = CatalogUpdateRequest

// Response type for API operations
export type EmployeeDepartmentResponse = EmployeeDepartment

// Filter type for list operations
export type EmployeeDepartmentFilters = CatalogFilters & {
  // Additional filters specific to EmployeeDepartment
  search?: string
  is_active?: boolean
  name_contains?: string
  code_contains?: string
}

// Paginated response type
export type EmployeeDepartmentPaginatedResponse = PaginatedResponse<EmployeeDepartment>

// This replaces ~30 lines of manual type definitions:
//
// export interface EmployeeDepartment {
//   id: UUID
//   tenant_id: UUID
//   code?: string
//   name: string
//   description?: string
//   is_active: boolean
//   created_at: string
//   updated_at: string
// }
//
// export interface EmployeeDepartmentCreate {
//   code?: string
//   name: string
//   description?: string
//   is_active?: boolean
// }
//
// export interface EmployeeDepartmentUpdate {
//   code?: string
//   name?: string
//   description?: string
//   is_active?: boolean
// }
