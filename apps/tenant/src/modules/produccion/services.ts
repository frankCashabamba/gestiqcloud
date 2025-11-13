import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'

export type ProductionOrder = {
    id: string
    numero?: string
    recipe_id?: string
    product_id?: string
    warehouse_id?: string
    qty_planned: number
    qty_produced?: number
    waste_qty?: number
    scheduled_date?: string
    started_at?: string
    completed_at?: string
    status?: 'draft' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
    batch_number?: string
    notes?: string
    created_at?: string
    updated_at?: string
}

export type Recipe = {
    id: string
    name: string
    product_id: string
    rendimiento: number
    tiempo_preparacion?: number
    instrucciones?: string
    ingredientes?: RecipeIngredient[]
    created_at?: string
    updated_at?: string
}

export type RecipeIngredient = {
    id?: string
    recipe_id?: string
    product_id: string
    cantidad: number
    unidad?: string
}

export async function listProductionOrders(): Promise<ProductionOrder[]> {
    const { data } = await tenantApi.get<ProductionOrder[] | { items?: ProductionOrder[] }>('/api/v1/production/orders')
    return ensureArray<ProductionOrder>(data)
}

export async function getProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.get<ProductionOrder>(`/api/v1/production/orders/${id}`)
    return data
}

export async function createProductionOrder(payload: Omit<ProductionOrder, 'id'>): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>('/api/v1/production/orders', payload)
    return data
}

export async function updateProductionOrder(id: string, payload: Partial<ProductionOrder>): Promise<ProductionOrder> {
    const { data } = await tenantApi.put<ProductionOrder>(`/api/v1/production/orders/${id}`, payload)
    return data
}

export async function removeProductionOrder(id: string): Promise<void> {
    await tenantApi.delete(`/api/v1/production/orders/${id}`)
}

export async function startProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/production/orders/${id}/start`, {})
    return data
}

export async function completeProductionOrder(id: string, payload: { qty_produced: number; waste_qty?: number }): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/production/orders/${id}/complete`, payload)
    return data
}

export async function cancelProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/production/orders/${id}/cancel`, {})
    return data
}

export async function listRecipes(): Promise<Recipe[]> {
    const { data } = await tenantApi.get<Recipe[] | { items?: Recipe[] }>('/api/v1/production/recipes')
    return ensureArray<Recipe>(data)
}

export async function getRecipe(id: string): Promise<Recipe> {
    const { data } = await tenantApi.get<Recipe>(`/api/v1/production/recipes/${id}`)
    return data
}

export async function createRecipe(payload: Omit<Recipe, 'id'>): Promise<Recipe> {
    const { data } = await tenantApi.post<Recipe>('/api/v1/production/recipes', payload)
    return data
}

export async function updateRecipe(id: string, payload: Partial<Recipe>): Promise<Recipe> {
    const { data } = await tenantApi.put<Recipe>(`/api/v1/production/recipes/${id}`, payload)
    return data
}

export async function removeRecipe(id: string): Promise<void> {
    await tenantApi.delete(`/api/v1/production/recipes/${id}`)
}
