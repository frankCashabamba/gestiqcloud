/**
 * API Service - Production Cost Drivers & Recipe Cost Lines
 */

import { apiClient } from './client';
import { TENANT_RECIPES, TENANT_COST_DRIVERS, TENANT_COST_DRIVER_UNIT_TYPES } from '@shared/endpoints';

// ============================================================================
// TYPES
// ============================================================================

export interface CostDriver {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  unit: string;
  default_rate: number;
  consumption_rate: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CostDriverCreate {
  code: string;
  name: string;
  unit?: string;
  default_rate?: number;
  consumption_rate?: number | null;
  is_active?: boolean;
}

export interface CostDriverUnitType {
  id: string;
  code: string;
  name_en: string;
  name_es: string | null;
  is_active: boolean;
  sort_order: number;
}

export interface RecipeCostLine {
  id: string;
  recipe_id: string;
  driver_id: string;
  qty_standard: number;
  headcount: number;
  rate_override: number | null;
  notes: string | null;
  line_order: number;
  created_at: string;
  driver_code: string | null;
  driver_name: string | null;
  driver_unit: string | null;
  driver_default_rate: number | null;
  driver_consumption_rate: number | null;
  effective_rate: number | null;
  line_cost: number | null;
}

export interface RecipeCostLineCreate {
  driver_id: string;
  qty_standard: number;
  headcount?: number;
  rate_override?: number | null;
  notes?: string;
  line_order?: number;
}

export interface FullCostSummary {
  recipe_id: string;
  recipe_name: string;
  yield_qty: number;
  materials_total: number;
  materials_unit: number;
  labor_total: number;
  labor_with_burden_factor: number;
  energy_total: number;
  other_indirect_total: number;
  indirect_total: number;
  labor_burden_factor: number;
  diesel_total: number;
  electricity_total: number;
  full_cost_total: number;
  full_cost_unit: number;
  cost_lines: RecipeCostLine[];
  period_month?: string | null;
  period_id?: string | null;
  touch_minutes?: number;
  oven_minutes?: number;
  trays_per_batch?: number | null;
  units_per_tray?: number | null;
  breakdown?: {
    materials: number;
    labor: number;
    diesel: number;
    electricity: number;
    other: number;
  };
}

// ============================================================================
// COST DRIVERS
// ============================================================================

export async function listCostDrivers(): Promise<CostDriver[]> {
  const res = await apiClient.get(TENANT_COST_DRIVERS.list);
  return res.data;
}

export async function listCostDriverUnitTypes(): Promise<CostDriverUnitType[]> {
  const res = await apiClient.get(TENANT_COST_DRIVER_UNIT_TYPES.list);
  return res.data;
}

export async function createCostDriver(data: CostDriverCreate): Promise<CostDriver> {
  const res = await apiClient.post(TENANT_COST_DRIVERS.list, data);
  return res.data;
}

export async function updateCostDriver(id: string, data: Partial<CostDriverCreate>): Promise<CostDriver> {
  const res = await apiClient.put(TENANT_COST_DRIVERS.byId(id), data);
  return res.data;
}

export async function deleteCostDriver(id: string): Promise<void> {
  await apiClient.delete(TENANT_COST_DRIVERS.byId(id));
}

// ============================================================================
// RECIPE COST LINES
// ============================================================================

export async function listRecipeCostLines(recipeId: string): Promise<RecipeCostLine[]> {
  const res = await apiClient.get(TENANT_RECIPES.costLines(recipeId));
  return res.data;
}

export async function addRecipeCostLine(recipeId: string, data: RecipeCostLineCreate): Promise<RecipeCostLine> {
  const res = await apiClient.post(TENANT_RECIPES.costLines(recipeId), data);
  return res.data;
}

export async function updateRecipeCostLine(
  recipeId: string, lineId: string, data: Partial<RecipeCostLineCreate>
): Promise<RecipeCostLine> {
  const res = await apiClient.put(TENANT_RECIPES.costLineById(recipeId, lineId), data);
  return res.data;
}

export async function deleteRecipeCostLine(recipeId: string, lineId: string): Promise<void> {
  await apiClient.delete(TENANT_RECIPES.costLineById(recipeId, lineId));
}

// ============================================================================
// FULL COST
// ============================================================================

export async function getRecipeFullCost(recipeId: string): Promise<FullCostSummary> {
  const res = await apiClient.get(TENANT_RECIPES.fullCost(recipeId));
  return res.data;
}
