/**
 * Catalog services using centralized types from @packages/api-types
 * This replaces duplicated type definitions across admin/tenant.
 */

import api from '../shared/api/client'
import type {
  BusinessType,
  BusinessCategory,
  SectorTemplate,
  CatalogLanguage,
  CatalogCurrency,
  CatalogCountry,
  CatalogCreateRequest,
  CatalogUpdateRequest,
  CatalogFilters,
  CatalogResponse,
  PaginatedResponse,
  UUID
} from '@packages/api-types'

// Business Types API
export async function listBusinessTypes(
  tenantId: string,
  filters: CatalogFilters = {}
): Promise<PaginatedResponse<BusinessType>> {
  const params = new URLSearchParams()
  
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.per_page) params.append('per_page', filters.per_page.toString())
  if (filters.search) params.append('search', filters.search)
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString())
  
  const response = await api.get(`/api/v1/tenant/business-types?${params}`)
  return response.data
}

export async function getBusinessType(
  tenantId: string,
  id: UUID
): Promise<BusinessType> {
  const response = await api.get(`/api/v1/tenant/business-types/${id}`)
  return response.data
}

export async function createBusinessType(
  tenantId: string,
  data: CatalogCreateRequest
): Promise<BusinessType> {
  const response = await api.post(`/api/v1/tenant/business-types`, data)
  return response.data
}

export async function updateBusinessType(
  tenantId: string,
  id: UUID,
  data: CatalogUpdateRequest
): Promise<BusinessType> {
  const response = await api.put(`/api/v1/tenant/business-types/${id}`, data)
  return response.data
}

export async function deleteBusinessType(
  tenantId: string,
  id: UUID
): Promise<void> {
  await api.delete(`/api/v1/tenant/business-types/${id}`)
}

// Business Categories API (similar pattern)
export async function listBusinessCategories(
  tenantId: string,
  filters: CatalogFilters = {}
): Promise<PaginatedResponse<BusinessCategory>> {
  const params = new URLSearchParams()
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value.toString())
    }
  })
  
  const response = await api.get(`/api/v1/tenant/business-categories?${params}`)
  return response.data
}

export async function getBusinessCategory(
  tenantId: string,
  id: UUID
): Promise<BusinessCategory> {
  const response = await api.get(`/api/v1/tenant/business-categories/${id}`)
  return response.data
}

export async function createBusinessCategory(
  tenantId: string,
  data: CatalogCreateRequest
): Promise<BusinessCategory> {
  const response = await api.post(`/api/v1/tenant/business-categories`, data)
  return response.data
}

export async function updateBusinessCategory(
  tenantId: string,
  id: UUID,
  data: CatalogUpdateRequest
): Promise<BusinessCategory> {
  const response = await api.put(`/api/v1/tenant/business-categories/${id}`, data)
  return response.data
}

export async function deleteBusinessCategory(
  tenantId: string,
  id: UUID
): Promise<void> {
  await api.delete(`/api/v1/tenant/business-categories/${id}`)
}

// Sector Templates API
export async function listSectorTemplates(
  tenantId: string,
  filters: CatalogFilters = {}
): Promise<PaginatedResponse<SectorTemplate>> {
  const params = new URLSearchParams()
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value.toString())
    }
  })
  
  const response = await api.get(`/api/v1/tenant/sector-templates?${params}`)
  return response.data
}

export async function getSectorTemplate(
  tenantId: string,
  id: UUID
): Promise<SectorTemplate> {
  const response = await api.get(`/api/v1/tenant/sector-templates/${id}`)
  return response.data
}

// System Catalogs (no tenant required)
export async function listLanguages(): Promise<CatalogLanguage[]> {
  const response = await api.get('/api/v1/languages')
  return response.data
}

export async function listCurrencies(): Promise<CatalogCurrency[]> {
  const response = await api.get('/api/v1/currencies')
  return response.data
}

export async function listCountries(): Promise<CatalogCountry[]> {
  const response = await api.get('/api/v1/countries')
  return response.data
}

// Generic catalog service for reuse
export function createCatalogService<T extends { id: UUID }>(
  endpoint: string
) {
  return {
    list: (tenantId: string, filters: CatalogFilters = {}): Promise<PaginatedResponse<T>> => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString())
        }
      })
      return api.get(`/api/v1/tenant/${endpoint}?${params}`).then(r => r.data)
    },
    
    get: (tenantId: string, id: UUID): Promise<T> => {
      return api.get(`/api/v1/tenant/${endpoint}/${id}`).then(r => r.data)
    },
    
    create: (tenantId: string, data: CatalogCreateRequest): Promise<T> => {
      return api.post(`/api/v1/tenant/${endpoint}`, data).then(r => r.data)
    },
    
    update: (tenantId: string, id: UUID, data: CatalogUpdateRequest): Promise<T> => {
      return api.put(`/api/v1/tenant/${endpoint}/${id}`, data).then(r => r.data)
    },
    
    delete: (tenantId: string, id: UUID): Promise<void> => {
      return api.delete(`/api/v1/tenant/${endpoint}/${id}`)
    }
  }
}

// Usage example:
// const businessTypeService = createCatalogService<BusinessType>('business-types')
// const items = await businessTypeService.list(tenantId, { page: 1, per_page: 20 })
