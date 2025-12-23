/**
 * API Service - Recetas
 * 12 funciones completas para gestión de recetas
 */

import { apiClient } from './client';
import { TENANT_RECIPES } from '@shared/endpoints';

// ============================================================================
// TYPES
// ============================================================================

export interface RecipeIngredient {
  product_id: string;
  qty: number;
  unit: string;
  purchase_packaging: string;
  qty_per_package: number;
  package_unit: string;
  package_cost: number;
  notes?: string;
  line_order?: number;
}

export interface RecipeCreate {
  name: string;
  product_id: string;
  yield_qty: number;
  prep_time_minutes?: number;
  instructions?: string;
  is_active?: boolean;
  ingredients?: RecipeIngredient[];
}

export interface RecipeUpdate {
  name?: string;
  product_id?: string;
  yield_qty?: number;
  prep_time_minutes?: number;
  instructions?: string;
  is_active?: boolean;
}

export interface Recipe {
  id: string;
  tenant_id: string;
  product_id: string;
  name: string;
  yield_qty: number;
  total_cost: number;
  unit_cost: number;
  prep_time_minutes?: number;
  instructions?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  product_name?: string;
  ingredients?: RecipeIngredientResponse[];
}

export interface RecipeIngredientResponse extends RecipeIngredient {
  id: string;
  recipe_id: string;
  ingredient_cost: number;
  created_at: string;
  product_name?: string;
}

export interface CostBreakdown {
  recipe_id: string;
  name: string;
  rendimiento: number;
  costo_total: number;
  costo_por_unidad: number;
  ingredientes_count: number;
  desglose: Array<{
    producto_id: string;
    producto: string;
    qty: number;
    unidad: string;
    presentacion_compra: string;
    costo: number;
    porcentaje: number;
  }>;
}

export interface ProductionCalculation {
  recipe: {
    id: string;
    name: string;
    rendimiento: number;
  };
  qty_to_produce: number;
  batches_required: number;
  ingredientes: Array<{
    producto_id: string;
    producto: string;
    qty_necesaria: number;
    unidad: string;
    presentaciones_necesarias: number;
    presentacion_compra: string;
    costo_estimado: number;
  }>;
  costo_total_produccion: number;
  costo_por_unidad: number;
  tiempo_estimado?: {
    batches: number;
    tiempo_por_batch_min: number;
    tiempo_total_min: number;
    tiempo_total_horas: number;
    workers: number;
  };
}

export interface ProfitabilityAnalysis {
  recipe_id: string;
  name: string;
  costo_directo: number;
  costo_indirecto: number;
  costo_total: number;
  precio_venta: number;
  ganancia: number;
  margen_porcentaje: number;
  punto_equilibrio_unidades: number;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * 1. Crear receta
 */
export async function createRecipe(data: RecipeCreate): Promise<Recipe> {
  const response = await apiClient.post(TENANT_RECIPES.list, data);
  return response.data;
}

/**
 * 2. Listar recetas
 */
export async function listRecipes(params?: {
  activo?: boolean;
  product_id?: string;
  skip?: number;
  limit?: number;
}): Promise<Recipe[]> {
  const response = await apiClient.get(TENANT_RECIPES.list, { params });
  return response.data;
}

/**
 * 3. Obtener detalle de receta
 */
export async function getRecipe(recipeId: string): Promise<Recipe> {
  const response = await apiClient.get(TENANT_RECIPES.byId(recipeId));
  return response.data;
}

/**
 * 4. Actualizar receta
 */
export async function updateRecipe(
  recipeId: string,
  data: RecipeUpdate
): Promise<Recipe> {
  const response = await apiClient.put(TENANT_RECIPES.byId(recipeId), data);
  return response.data;
}

/**
 * 5. Eliminar receta
 */
export async function deleteRecipe(recipeId: string): Promise<void> {
  await apiClient.delete(TENANT_RECIPES.byId(recipeId));
}

/**
 * 6. Agregar ingrediente
 */
export async function addIngredient(
  recipeId: string,
  data: RecipeIngredient
): Promise<RecipeIngredientResponse> {
  const response = await apiClient.post(
    TENANT_RECIPES.addIngredient(recipeId),
    data
  );
  return response.data;
}

/**
 * 7. Actualizar ingrediente
 */
export async function updateIngredient(
  recipeId: string,
  ingredientId: string,
  data: Partial<RecipeIngredient>
): Promise<RecipeIngredientResponse> {
  const response = await apiClient.put(
    TENANT_RECIPES.updateIngredient(recipeId, ingredientId),
    data
  );
  return response.data;
}

/**
 * 8. Eliminar ingrediente
 */
export async function deleteIngredient(
  recipeId: string,
  ingredientId: string
): Promise<void> {
  await apiClient.delete(TENANT_RECIPES.deleteIngredient(recipeId, ingredientId));
}

/**
 * 9. Obtener desglose de costos
 */
export async function getCostBreakdown(
  recipeId: string
): Promise<CostBreakdown> {
  const response = await apiClient.get(TENANT_RECIPES.costBreakdown(recipeId));
  return response.data;
}

/**
 * 10. Calcular producción
 */
export async function calculateProduction(
  recipeId: string,
  qtyToProduce: number,
  workers?: number
): Promise<ProductionCalculation> {
  const response = await apiClient.post(
    TENANT_RECIPES.calculateProduction(recipeId),
    {
      qty_to_produce: qtyToProduce,
      workers,
    }
  );
  return response.data;
}

/**
 * 11. Crear orden de compra
 */
export async function createPurchaseOrder(
  recipeId: string,
  qtyToProduce: number,
  supplierId?: string
): Promise<any> {
  const response = await apiClient.post(
    TENANT_RECIPES.purchaseOrder(recipeId),
    {
      qty_to_produce: qtyToProduce,
      supplier_id: supplierId,
    }
  );
  return response.data;
}

/**
 * 12. Calcular rentabilidad
 */
export async function calculateProfitability(
  recipeId: string,
  sellingPrice: number,
  indirectCostsPct: number = 0.3
): Promise<ProfitabilityAnalysis> {
  const response = await apiClient.post(TENANT_RECIPES.profitability(recipeId), {
    selling_price: sellingPrice,
    indirect_costs_pct: indirectCostsPct,
  });
  return response.data;
}

/**
 * 13. Comparar recetas
 */
export async function compareRecipes(
  recipeIds: string[]
): Promise<{ recipes: any[] }> {
  const response = await apiClient.post(TENANT_RECIPES.compare, recipeIds);
  return response.data;
}
