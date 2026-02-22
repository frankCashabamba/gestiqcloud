/**
 * Costing Module API Service
 * Real cost calculation endpoints for recipes and cost periods
 */

import tenantApi from '../shared/api/client'
import {
  CostPeriod,
  CostPeriodCreate,
  CostPeriodImpact,
  CostPeriodUpdate,
  CostPeriodValidation,
  CreateRecipePayload,
  RecipeCostBreakdown,
  RecipeStep,
  RecipeStepCreate,
  RecipeWithCosts,
} from '../types/costing'

const BASE = '/api/v1/tenant/production'

// ============================================================================
// RECIPES API
// ============================================================================

export const recipesApi = {
  list: async (): Promise<RecipeWithCosts[]> => {
    const { data } = await tenantApi.get<RecipeWithCosts[]>(`${BASE}/recipes`)
    return Array.isArray(data) ? data : []
  },

  get: async (recipeId: string): Promise<RecipeWithCosts> => {
    const { data } = await tenantApi.get<RecipeWithCosts>(`${BASE}/recipes/${recipeId}`)
    return data
  },

  getCost: async (recipeId: string): Promise<RecipeCostBreakdown> => {
    const { data } = await tenantApi.get<RecipeCostBreakdown>(`${BASE}/recipes/${recipeId}/cost-breakdown`)
    return data
  },

  getFullCost: async (recipeId: string, periodMonth?: string): Promise<RecipeCostBreakdown> => {
    const params = periodMonth ? { period_month: periodMonth } : {}
    const { data } = await tenantApi.get<RecipeCostBreakdown>(`${BASE}/recipes/${recipeId}/full-cost`, { params })
    return data
  },

  create: async (payload: CreateRecipePayload): Promise<RecipeWithCosts> => {
    const { data } = await tenantApi.post<RecipeWithCosts>(`${BASE}/recipes`, payload)
    return data
  },

  update: async (recipeId: string, payload: Partial<CreateRecipePayload>): Promise<RecipeWithCosts> => {
    const { data } = await tenantApi.put<RecipeWithCosts>(`${BASE}/recipes/${recipeId}`, payload)
    return data
  },

  delete: async (recipeId: string): Promise<void> => {
    await tenantApi.delete(`${BASE}/recipes/${recipeId}`)
  },

  // Recipe Steps
  getSteps: async (recipeId: string): Promise<RecipeStep[]> => {
    const { data } = await tenantApi.get<RecipeStep[]>(`${BASE}/recipes/${recipeId}/steps`)
    return Array.isArray(data) ? data : []
  },

  addStep: async (recipeId: string, payload: RecipeStepCreate): Promise<RecipeStep> => {
    const { data } = await tenantApi.post<RecipeStep>(`${BASE}/recipes/${recipeId}/steps`, payload)
    return data
  },

  updateStep: async (recipeId: string, stepId: string, payload: Partial<RecipeStepCreate>): Promise<RecipeStep> => {
    const { data } = await tenantApi.put<RecipeStep>(`${BASE}/recipes/${recipeId}/steps/${stepId}`, payload)
    return data
  },

  deleteStep: async (recipeId: string, stepId: string): Promise<void> => {
    await tenantApi.delete(`${BASE}/recipes/${recipeId}/steps/${stepId}`)
  },
}

// ============================================================================
// COST PERIODS API
// ============================================================================

export const costPeriodsApi = {
  list: async (): Promise<CostPeriod[]> => {
    const { data } = await tenantApi.get<CostPeriod[]>(`${BASE}/cost-periods`)
    return Array.isArray(data) ? data : []
  },

  get: async (periodId: string): Promise<CostPeriod> => {
    const { data } = await tenantApi.get<CostPeriod>(`${BASE}/cost-periods/${periodId}`)
    return data
  },

  create: async (payload: CostPeriodCreate): Promise<CostPeriod> => {
    const { data } = await tenantApi.post<CostPeriod>(`${BASE}/cost-periods`, payload)
    return data
  },

  update: async (periodId: string, payload: CostPeriodUpdate): Promise<CostPeriod> => {
    const { data } = await tenantApi.put<CostPeriod>(`${BASE}/cost-periods/${periodId}`, payload)
    return data
  },

  delete: async (periodId: string): Promise<void> => {
    await tenantApi.delete(`${BASE}/cost-periods/${periodId}`)
  },

  validate: async (periodId: string): Promise<CostPeriodValidation> => {
    const { data } = await tenantApi.get<CostPeriodValidation>(`${BASE}/cost-periods/${periodId}/validate`)
    return data
  },

  getImpact: async (periodId: string): Promise<CostPeriodImpact> => {
    const { data } = await tenantApi.get<CostPeriodImpact>(`${BASE}/cost-periods/${periodId}/impact`)
    return data
  },

  close: async (periodId: string): Promise<CostPeriod> => {
    const { data } = await tenantApi.post<CostPeriod>(`${BASE}/cost-periods/${periodId}/close`, {})
    return data
  },
}
