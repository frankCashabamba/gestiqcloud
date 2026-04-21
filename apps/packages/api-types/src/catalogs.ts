/**
 * Types for catalog-like entities (shared between admin and tenant)
 */

import type { UUID, Timestamp } from './common'

// Base catalog interface
export interface BaseCatalog {
  id: UUID
  tenant_id?: UUID // Optional for system-wide catalogs
  code?: string
  name: string
  description?: string
  is_active: boolean
  created_at: Timestamp
  updated_at: Timestamp
}

// Business catalogs
export interface BusinessType extends BaseCatalog {
  tenant_id: UUID
}

export interface BusinessCategory extends BaseCatalog {
  tenant_id: UUID
}

export interface SectorTemplate extends BaseCatalog {
  tenant_id: UUID
  template_config?: Record<string, unknown>
  config_version?: number
}

// System catalogs (no tenant_id)
export interface CatalogLanguage extends Omit<BaseCatalog, 'tenant_id'> {
  code: string // Required for system catalogs
}

export interface CatalogCurrency extends Omit<BaseCatalog, 'tenant_id'> {
  code: string // Required for system catalogs
  symbol: string
}

export interface CatalogCountry extends Omit<BaseCatalog, 'tenant_id'> {
  code: string // Required for system catalogs
}

export interface Weekday extends Omit<BaseCatalog, 'tenant_id'> {
  key: string
  order: number
}

// HR catalogs
export interface EmployeeDepartment extends BaseCatalog {
  tenant_id: UUID
}

export interface PayrollConcept extends BaseCatalog {
  tenant_id: UUID
  concept_type: 'EARNING' | 'DEDUCTION'
  amount?: number
  is_base?: boolean
}

// Expense catalogs
export interface ExpenseCategory extends BaseCatalog {
  tenant_id: UUID
}

// Product catalogs
export interface ProductCategory extends BaseCatalog {
  tenant_id: UUID
  parent_id?: UUID
}

// POS catalogs
export interface POSRegister extends BaseCatalog {
  tenant_id: UUID
  store_id?: UUID
}

export interface PaymentMethod extends BaseCatalog {
  tenant_id: UUID
  is_default?: boolean
}

// Common CRUD operations
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
  search?: string
  is_active?: boolean
  code?: string
  page?: number
  per_page?: number
}

export interface CatalogResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}
