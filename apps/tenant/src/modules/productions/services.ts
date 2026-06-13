import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_PRODUCTION_ORDERS, TENANT_PRODUCTION_PLANNING, TENANT_RECIPES } from '@shared/endpoints'

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

export type ListProductionOrdersParams = {
    skip?: number
    limit?: number
    status?: ProductionOrder['status']
    recipe_id?: string
    date_from?: string
    date_to?: string
    scheduled_from?: string
    scheduled_to?: string
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

export type ProductionPlanningSuggestion = {
    recipe_id: string
    product_id: string
    recipe_name: string
    product_name: string
    target_date: string
    avg_daily_sales: number
    stock_on_hand: number
    already_planned_qty: number
    suggested_qty: number
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

function serializeProductionOrderPayload(payload: Partial<ProductionOrder>) {
    if (!payload.status) return payload
    return {
        ...payload,
        status: String(payload.status).toUpperCase(),
    }
}

export async function listProductionOrders(params?: ListProductionOrdersParams): Promise<ProductionOrder[]> {
    const { data } = await tenantApi.get<ProductionOrder[] | { items?: ProductionOrder[] }>(TENANT_PRODUCTION_ORDERS.base, {
        params,
    })
    return ensureArray<ProductionOrder>(data).map(normalizeProductionOrder)
}

export async function getProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.get<ProductionOrder>(TENANT_PRODUCTION_ORDERS.byId(id))
    return normalizeProductionOrder(data)
}

export async function createProductionOrder(payload: Omit<ProductionOrder, 'id'>): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(
        TENANT_PRODUCTION_ORDERS.base,
        serializeProductionOrderPayload(payload)
    )
    return normalizeProductionOrder(data)
}

export async function updateProductionOrder(id: string, payload: Partial<ProductionOrder>): Promise<ProductionOrder> {
    const { data } = await tenantApi.put<ProductionOrder>(
        TENANT_PRODUCTION_ORDERS.byId(id),
        serializeProductionOrderPayload(payload)
    )
    return normalizeProductionOrder(data)
}

export async function removeProductionOrder(id: string): Promise<void> {
    await tenantApi.delete(TENANT_PRODUCTION_ORDERS.byId(id))
}

export async function startProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(TENANT_PRODUCTION_ORDERS.start(id), {})
    return normalizeProductionOrder(data)
}

export async function completeProductionOrder(id: string, payload: ProductionOrderCompleteInput): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(TENANT_PRODUCTION_ORDERS.complete(id), payload)
    return normalizeProductionOrder(data)
}

export async function listProductionOrderCosts(id: string): Promise<ProductionOrderCost[]> {
    const { data } = await tenantApi.get<ProductionOrderCost[]>(TENANT_PRODUCTION_ORDERS.costs(id))
    return Array.isArray(data) ? data : []
}

export async function replaceProductionOrderCosts(
    id: string,
    payload: ProductionOrderCostInput[],
): Promise<ProductionOrderCost[]> {
    const { data } = await tenantApi.put<ProductionOrderCost[]>(TENANT_PRODUCTION_ORDERS.costs(id), payload)
    return Array.isArray(data) ? data : []
}

export async function cancelProductionOrder(id: string): Promise<ProductionOrder> {
    const { data } = await tenantApi.post<ProductionOrder>(TENANT_PRODUCTION_ORDERS.cancel(id), {})
    return normalizeProductionOrder(data)
}

export async function listProductionPlanningSuggestions(params?: {
    target_date?: string
    history_days?: number
    limit?: number
}): Promise<ProductionPlanningSuggestion[]> {
    const { data } = await tenantApi.get<ProductionPlanningSuggestion[]>(
        TENANT_PRODUCTION_PLANNING.suggestions,
        { params }
    )
    return Array.isArray(data)
        ? data.map((item) => ({
            ...item,
            avg_daily_sales: Number(item.avg_daily_sales || 0),
            stock_on_hand: Number(item.stock_on_hand || 0),
            already_planned_qty: Number(item.already_planned_qty || 0),
            suggested_qty: Number(item.suggested_qty || 0),
        }))
        : []
}

export async function listRecipes(): Promise<Recipe[]> {
    const { data } = await tenantApi.get<Recipe[] | { items?: Recipe[] }>(TENANT_RECIPES.list)
    return ensureArray<Recipe>(data)
}

export async function getRecipe(id: string): Promise<Recipe> {
    const { data } = await tenantApi.get<Recipe>(TENANT_RECIPES.byId(id))
    return data
}

export async function createRecipe(payload: Omit<Recipe, 'id'>): Promise<Recipe> {
    const { data } = await tenantApi.post<Recipe>(TENANT_RECIPES.base, payload)
    return data
}

export async function updateRecipe(id: string, payload: Partial<Recipe>): Promise<Recipe> {
    const { data } = await tenantApi.put<Recipe>(TENANT_RECIPES.byId(id), payload)
    return data
}

export async function removeRecipe(id: string): Promise<void> {
    await tenantApi.delete(TENANT_RECIPES.byId(id))
}
