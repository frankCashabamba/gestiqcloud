/**
 * Business Categories API Service
 *
 * Servicio para obtener categorías de negocio desde API dinámica.
 * Reemplaza hardcoding anterior.
 *
 * Endpoints:
 * - GET /api/v1/business-categories - Listar todas
 * - GET /api/v1/business-categories/{code} - Obtener por código
 */

import tenantApi from '../shared/api/client'

export interface BusinessCategory {
  id: string
  code: string
  name: string
  description?: string
  is_active?: boolean
}

export interface BusinessCategoriesResponse {
  ok: boolean
  count: number
  categories: BusinessCategory[]
}

export interface BusinessCategoryResponse {
  ok: boolean
  category: BusinessCategory
}

/**
 * Obtiene todas las categorías de negocio activas desde BD
 */
export async function getBusinessCategories(): Promise<BusinessCategory[]> {
  try {
    const response = await tenantApi.get<BusinessCategoriesResponse>(
      '/api/v1/business-categories'
    )

    if (!response.data.ok) {
      console.warn('Error en respuesta de categorías:', response.data)
      return []
    }

    return response.data.categories || []
  } catch (error) {
    console.error('Error obteniendo categorías de negocio:', error)
    return []
  }
}

/**
 * Obtiene una categoría específica por su código
 */
export async function getBusinessCategoryByCode(
  code: string
): Promise<BusinessCategory | null> {
  try {
    const response = await tenantApi.get<BusinessCategoryResponse>(
      `/api/v1/business-categories/${code}`
    )

    if (!response.data.ok) {
      console.warn(`Categoría '${code}' no encontrada`)
      return null
    }

    return response.data.category || null
  } catch (error) {
    console.error(`Error obteniendo categoría '${code}':`, error)
    return null
  }
}

/**
 * Hook alternativo para cargar categorías en componentes
 * (simplificado para uso directo)
 */
export function useBusinessCategories() {
  return {
    getAll: getBusinessCategories,
    getByCode: getBusinessCategoryByCode,
  }
}

export const getByCode = getBusinessCategoryByCode
