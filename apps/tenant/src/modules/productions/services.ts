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
    waste_reason?: string
    scheduled_date?: string
    started_at?: string
    completed_at?: string
    status?: 'draft' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
    batch_number?: string
    notes?: string
    created_at?: string
    updated_at?: string
}

export type ProductionOrderCompleteInput = {
    qty_produced: number
    waste_qty?: number
    waste_reason?: string
    batch_number?: string
    notes?: string
}

export type ProductionOrderCost = {
    id: string
    order_id: string
    driver_id: string
    qty_actual: number
    headcount_actual: number
    rate_applied: number
    cost_total: number
    notes?: string | null
    created_at?: string
    driver_code?: string | null
    driver_name?: string | null
    driver_unit?: string | null
}

export type ProductionOrderCostInput = {
    driver_id: string
    qty_actual: number
    headcount_actual?: number
    rate_applied: number
    notes?: string | null
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

function normalizeProductionStatus(
    status?: string,
): ProductionOrder['status'] | undefined {
    if (!status) return undefined
    const normalized = status.toLowerCase()
    if (
        normalized === 'draft' ||
        normalized === 'scheduled' ||
        normalized === 'in_progress' ||
        normalized === 'completed' ||
        normalized === 'cancelled'
    ) {
        return normalized
    }
    return undefined
}

function normalizeProductionOrder(order: ProductionOrder): ProductionOrder {
    return {
        ...order,
        qty_planned: Number(order.qty_planned || 0),
        qty_produced: order.qty_produced != null ? Number(order.qty_produced) : undefined,
        waste_qty: order.waste_qty != null ? Number(order.waste_qty) : undefined,
        status: normalizeProductionStatus(order.status),
    }
}

export async function listProductionOrders(): Promise<ProductionOrder[]> {
    const { data } = await tenantApi.get<ProductionOrder[] | { items?: ProductionOrder[] }>('/api/v1/tenant/production/orders')
    return ensureArray<ProductionOrder>(data).map(normalizeProductionOrder)
}

export async function getProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.get<ProductionOrder>(`/api/v1/tenant/production/orders/${id}`)
    return normalizeProductionOrder(data)
}

export async function createProductionOrder(payload: Omit<ProductionOrder, 'id'>): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>('/api/v1/tenant/production/orders', payload)
    return normalizeProductionOrder(data)
}

export async function updateProductionOrder(id: string, payload: Partial<ProductionOrder>): Promise<ProductionOrder> {
    const { data } = await tenantApi.put<ProductionOrder>(`/api/v1/tenant/production/orders/${id}`, payload)
    return normalizeProductionOrder(data)
}

export async function removeProductionOrder(id: string): Promise<void> {
    await tenantApi.delete(`/api/v1/tenant/production/orders/${id}`)
}

export async function startProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/tenant/production/orders/${id}/start`, {})
    return normalizeProductionOrder(data)
}

export async function completeProductionOrder(id: string, payload: ProductionOrderCompleteInput): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/tenant/production/orders/${id}/complete`, payload)
    return normalizeProductionOrder(data)
}

export async function listProductionOrderCosts(id: string): Promise<ProductionOrderCost[]> {
    const { data } = await tenantApi.get<ProductionOrderCost[]>(`/api/v1/tenant/production/orders/${id}/costs`)
    return Array.isArray(data) ? data : []
}

export async function replaceProductionOrderCosts(
    id: string,
    payload: ProductionOrderCostInput[],
): Promise<ProductionOrderCost[]> {
    const { data } = await tenantApi.put<ProductionOrderCost[]>(`/api/v1/tenant/production/orders/${id}/costs`, payload)
    return Array.isArray(data) ? data : []
}

export async function cancelProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(`/api/v1/tenant/production/orders/${id}/cancel`, {})
    return normalizeProductionOrder(data)
}

export async function listRecipes(): Promise<Recipe[]> {
    const { data } = await tenantApi.get<Recipe[] | { items?: Recipe[] }>('/api/v1/tenant/production/recipes')
    return ensureArray<Recipe>(data)
}

export async function getRecipe(id: string): Promise<Recipe> {
    const { data } = await tenantApi.get<Recipe>(`/api/v1/tenant/production/recipes/${id}`)
    return data
}

export async function createRecipe(payload: Omit<Recipe, 'id'>): Promise<Recipe> {
    const { data } = await tenantApi.post<Recipe>('/api/v1/tenant/production/recipes', payload)
    return data
}

export async function updateRecipe(id: string, payload: Partial<Recipe>): Promise<Recipe> {
    const { data } = await tenantApi.put<Recipe>(`/api/v1/tenant/production/recipes/${id}`, payload)
    return data
}

export async function removeRecipe(id: string): Promise<void> {
    await tenantApi.delete(`/api/v1/tenant/production/recipes/${id}`)
}
