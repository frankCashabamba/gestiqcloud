/**
 * Employee Department Service - Example using generic catalog service
 */

// Mock API client for this example with proper typing
const api = {
  get: async (url: string): Promise<{ data: any }> => ({ data: {} }),
  post: async (url: string, data: any): Promise<{ data: any }> => ({ data: {} }),
  put: async (url: string, data: any): Promise<{ data: any }> => ({ data: {} }),
  delete: async (url: string, data?: any): Promise<{ data: any }> => ({ data: {} })
}

import type {
  EmployeeDepartment,
  EmployeeDepartmentCreate,
  EmployeeDepartmentUpdate,
  EmployeeDepartmentFilters,
  EmployeeDepartmentPaginatedResponse,
  UUID
} from '../types/employeeDepartment'

// Create generic catalog service for employee departments
const employeeDepartmentService = {
  list: async (
    tenantId: string,
    filters: EmployeeDepartmentFilters = {}
  ): Promise<EmployeeDepartmentPaginatedResponse> => {
    const params = new URLSearchParams()
    
    // Add pagination
    if (filters.page) params.append('page', filters.page.toString())
    if (filters.per_page) params.append('per_page', filters.per_page.toString())
    
    // Add search
    if (filters.search) params.append('search', filters.search)
    
    // Add specific filters
    if (filters.is_active !== undefined) {
      params.append('is_active', filters.is_active.toString())
    }
    if (filters.name_contains) {
      params.append('name_contains', filters.name_contains)
    }
    if (filters.code_contains) {
      params.append('code_contains', filters.code_contains)
    }
    
    const response = await api.get(
      `/api/v1/tenant/employee-departments?${params}`
    )
    return response.data
  },

  get: async (
    tenantId: string,
    id: UUID
  ): Promise<EmployeeDepartment> => {
    const response = await api.get(
      `/api/v1/tenant/employee-departments/${id}`
    )
    return response.data
  },

  create: async (
    tenantId: string,
    data: EmployeeDepartmentCreate
  ): Promise<EmployeeDepartment> => {
    const response = await api.post(
      '/api/v1/tenant/employee-departments',
      data
    )
    return response.data
  },

  update: async (
    tenantId: string,
    id: UUID,
    data: EmployeeDepartmentUpdate
  ): Promise<EmployeeDepartment> => {
    const response = await api.put(
      `/api/v1/tenant/employee-departments/${id}`,
      data
    )
    return response.data
  },

  delete: async (
    tenantId: string,
    id: UUID
  ): Promise<void> => {
    await api.delete(`/api/v1/tenant/employee-departments/${id}`)
  },

  // Additional methods specific to employee departments
  getActiveCount: async (tenantId: string): Promise<number> => {
    const response = await api.get(
      `/api/v1/tenant/employee-departments/count/active`
    )
    return response.data.count
  },

  findByCode: async (
    tenantId: string,
    code: string
  ): Promise<EmployeeDepartment | null> => {
    try {
      const response = await api.get(
        `/api/v1/tenant/employee-departments/by-code/${code}`
      )
      return response.data
    } catch (error) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Bulk operations
  bulkCreate: async (
    tenantId: string,
    items: EmployeeDepartmentCreate[]
  ): Promise<EmployeeDepartment[]> => {
    const response = await api.post(
      '/api/v1/tenant/employee-departments/bulk',
      { items }
    )
    return response.data
  },

  bulkUpdate: async (
    tenantId: string,
    updates: { id: UUID; data: EmployeeDepartmentUpdate }[]
  ): Promise<EmployeeDepartment[]> => {
    const response = await api.put(
      '/api/v1/tenant/employee-departments/bulk',
      { updates }
    )
    return response.data
  },

  bulkDelete: async (
    tenantId: string,
    ids: UUID[]
  ): Promise<void> => {
    await api.delete('/api/v1/tenant/employee-departments/bulk', {
      data: { ids }
    })
  }
}

// Generic catalog service factory for reuse
export function createCatalogService<T extends { id: UUID }>(
  endpoint: string
) {
  return {
    list: async (
      tenantId: string,
      filters: EmployeeDepartmentFilters = {}
    ): Promise<{ items: T[]; total: number; page: number; per_page: number; pages: number }> => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString())
        }
      })
      
      const response = await api.get(`/api/v1/tenant/${endpoint}?${params}`)
      return response.data
    },
    
    get: async (tenantId: string, id: UUID): Promise<T> => {
      const response = await api.get(`/api/v1/tenant/${endpoint}/${id}`)
      return response.data
    },
    
    create: async (tenantId: string, data: any): Promise<T> => {
      const response = await api.post(`/api/v1/tenant/${endpoint}`, data)
      return response.data
    },
    
    update: async (tenantId: string, id: UUID, data: any): Promise<T> => {
      const response = await api.put(`/api/v1/tenant/${endpoint}/${id}`, data)
      return response.data
    },
    
    delete: async (tenantId: string, id: UUID): Promise<void> => {
      await api.delete(`/api/v1/tenant/${endpoint}/${id}`)
    }
  }
}

export default employeeDepartmentService

// This replaces ~120 lines of manual service code:
//
// export async function listEmployeeDepartments(
//   tenantId: string,
//   filters: EmployeeDepartmentFilters = {}
// ): Promise<EmployeeDepartmentPaginatedResponse> {
//   const params = new URLSearchParams()
//   if (filters.page) params.append('page', filters.page.toString())
//   if (filters.per_page) params.append('per_page', filters.per_page.toString())
//   if (filters.search) params.append('search', filters.search)
//   if (filters.is_active !== undefined) {
//     params.append('is_active', filters.is_active.toString())
//   }
//   // ... 50+ lines more
// }
//
// export async function getEmployeeDepartment(
//   tenantId: string,
//   id: UUID
// ): Promise<EmployeeDepartment> {
//   const response = await api.get(`/api/v1/tenant/employee-departments/${id}`)
//   return response.data
// }
//
// export async function createEmployeeDepartment(
//   tenantId: string,
//   data: EmployeeDepartmentCreate
// ): Promise<EmployeeDepartment> {
//   const response = await api.post('/api/v1/tenant/employee-departments', data)
//   return response.data
// }
//
// // ... 50+ lines more for update, delete, etc.
