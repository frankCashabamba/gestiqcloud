/**
 * Costing Module Types - Real cost calculation for recipes
 * Separates TOUCH time (active labor) from PROCESS time (passive)
 */

export interface RecipeStep {
  id: string;
  recipe_id: string;
  step_name: string;
  duration_minutes: number;
  is_touch: boolean;
  resource_type: 'labor' | 'oven' | 'mixer' | 'prover' | 'other';
  line_order: number;
  created_at: string;
}

export interface RecipeStepCreate {
  step_name: string;
  duration_minutes: number;
  is_touch: boolean;
  resource_type: 'labor' | 'oven' | 'mixer' | 'prover' | 'other';
  line_order?: number;
}

export interface RecipeStepUpdate extends Partial<RecipeStepCreate> {}

export interface CostPeriod {
  id: string;
  tenant_id: string;
  month: string; // YYYY-MM format
  labor_hour_rate: number;
  labor_paid_hours: number;
  touch_hours_total: number | null;
  electricity_cost: number;
  diesel_cost_month: number;
  oven_hours_total: number;
  production_share_pct: number | null;
  labor_burden_factor: number;
  diesel_per_oven_hour: number;
  electricity_per_hour: number;
  is_closed: boolean;
  validated_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CostPeriodCreate {
  month: string; // YYYY-MM
  labor_hour_rate: number;
  labor_paid_hours: number;
  touch_hours_total?: number | null;
  electricity_cost: number;
  diesel_cost_month: number;
  oven_hours_total: number;
  production_share_pct?: number | null;
}

export interface CostPeriodUpdate extends Partial<CostPeriodCreate> {}

export interface CostPeriodValidation {
  period_id: string;
  is_valid: boolean;
  warnings: string[];
  anomalies: {
    high_burden_factor?: boolean;
    low_oven_utilization?: boolean;
    high_touch_efficiency?: boolean;
  };
  recommendations: string[];
}

export interface RecipeCostBreakdown {
  recipe_id: string;
  recipe_name: string;
  yield_units: number;
  ingredients_cost: number;
  labor_direct_cost: number;
  labor_burden_cost: number;
  labor_total_cost: number;
  diesel_cost: number;
  electricity_cost: number;
  other_indirects: number;
  total_cost: number;
  unit_cost: number;
  period_id?: string;
  period_month?: string;
}

export interface CostPeriodImpact {
  period_id: string;
  month: string;
  recipes_affected: Array<{
    recipe_id: string;
    recipe_name: string;
    previous_unit_cost: number;
    new_unit_cost: number;
    cost_difference: number;
    cost_difference_pct: number;
  }>;
  summary: {
    total_recipes: number;
    avg_cost_increase_pct: number;
    max_cost_increase_pct: number;
    min_cost_increase_pct: number;
  };
}

export interface RecipeWithCosts {
  id: string;
  tenant_id: string;
  product_id: string;
  name: string;
  yield_qty: number;
  yield_units: string;
  touch_minutes_standard: number;
  oven_minutes_standard: number;
  process_minutes: number | null;
  prep_time_minutes: number;
  baking_time_minutes: number;
  oven_temp_celsius: number;
  rest_time_minutes: number;
  waste_pct: number;
  trays_per_batch: number;
  units_per_tray: number;
  instructions?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  cost_breakdown?: RecipeCostBreakdown;
  steps?: RecipeStep[];
}

export interface CreateRecipePayload {
  product_id: string;
  name: string;
  yield_qty: number;
  touch_minutes_standard: number;
  oven_minutes_standard: number;
  process_minutes?: number | null;
  prep_time_minutes: number;
  baking_time_minutes: number;
  oven_temp_celsius: number;
  rest_time_minutes: number;
  waste_pct: number;
  trays_per_batch: number;
  units_per_tray: number;
  instructions: string;
  is_active: boolean;
  ingredients?: Array<{
    product_id: string;
    qty: number;
    unit: string;
    purchase_packaging: string;
    qty_per_package: number;
    package_unit: string;
    package_cost: number;
    notes?: string;
    line_order?: number;
  }>;
}

export interface DashboardMetrics {
  total_recipes: number;
  active_recipes: number;
  total_cost_periods: number;
  current_period?: CostPeriod;
  average_unit_cost: number;
  highest_cost_recipe: { name: string; unit_cost: number };
  lowest_cost_recipe: { name: string; unit_cost: number };
}
