/**
 * RecetaDetail - Vista detallada de receta con desglose de costos
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Typography, Box, Alert, CircularProgress, Grid,
  TextField, Tabs, Tab
} from '@mui/material';
import { AutoFixHigh } from '@mui/icons-material';
import {
  getRecipe,
  getCostBreakdown,
  optimizeRecipe,
  updateRecipe,
  type Recipe,
  type CostBreakdown,
  type RecipeOptimizationResponse,
  type RecipeIngredientResponse,
} from '../../services/api/recetas';
import { listProducts, type Product } from '../../services/api/products';
import {
  listCostDrivers,
  listRecipeCostLines,
  addRecipeCostLine,
  updateRecipeCostLine,
  deleteRecipeCostLine,
  getRecipeFullCost,
  type CostDriver,
  type RecipeCostLine,
  type FullCostSummary,
} from '../../services/api/productionCosts';
import tenantApi from '../../shared/api/client';
import { usePermission } from '../../hooks/usePermission';
import { useCompanyConfig } from '../../contexts/CompanyConfigContext';
import { useToast } from '../../shared/toast';
import { useUnits } from '../../hooks/useUnits';
import { normalizeUnitCode, convertQtyToUnit } from '../../services/unitService';
import {
  fetchIngredientMasterRows,
  formatIngredientReference,
  type IngredientMasterRow,
} from './ingredientCatalog';
import type { IngredientInsightMeta } from './RecetaIngredientInsightDialog';

const RecetaIngredientsTab = React.lazy(() => import('./RecetaIngredientsTab'));
const RecetaParametersTab = React.lazy(() => import('./RecetaParametersTab'));
const RecetaCostsTab = React.lazy(() => import('./RecetaCostsTab'));
const RecetaIngredientInsightDialog = React.lazy(() => import('./RecetaIngredientInsightDialog'));
const RecetaOptimizerDialog = React.lazy(() => import('./RecetaOptimizerDialog'));

const HOUR_LIKE_DRIVER_UNITS = new Set(['h', 'hh', 'hr', 'hrs', 'hora', 'horas', 'hour', 'hours']);

const normalizeCostDriverUnit = (unit?: string | null): string =>
  String(unit || '').trim().toLowerCase().replace(/[^a-z]/g, '');

const isHourLikeDriverUnit = (unit?: string | null): boolean =>
  HOUR_LIKE_DRIVER_UNITS.has(normalizeCostDriverUnit(unit));

const isLaborAutoDriver = (driver?: CostDriver | null): boolean => {
  if (!driver) return false;
  const driverCode = (driver.code || '').toUpperCase();
  if (driverCode.startsWith('LABOR')) return true;
  return isHourLikeDriverUnit(driver.unit)
    && !driverCode.startsWith('ENERGY')
    && !driverCode.startsWith('DIESEL')
    && !driverCode.startsWith('FUEL')
    && !driverCode.startsWith('OVEN');
};

const dialogPaperSx = {
  borderRadius: 4,
  border: '1px solid #e2e8f0',
  backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)',
  boxShadow: '0 28px 80px rgba(15, 23, 42, 0.18)',
};

const sectionCardSx = {
  mb: 3,
  p: { xs: 2, md: 2.5 },
  borderRadius: 3,
  border: '1px solid #e7edf5',
  backgroundColor: '#ffffff',
  boxShadow: '0 12px 32px rgba(15, 23, 42, 0.05)',
};

const clickableSectionSx = {
  cursor: 'pointer',
  transition: 'border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease',
  '&:hover': {
    borderColor: '#bfdbfe',
    boxShadow: '0 16px 40px rgba(37, 99, 235, 0.10)',
    transform: 'translateY(-1px)',
  },
};

const metricCardSx = {
  height: '100%',
  p: 1.75,
  borderRadius: 2.5,
  border: '1px solid #e8eef5',
  backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)',
};

const fieldGroupSx = {
  '& .MuiTextField-root': {
    '& .MuiOutlinedInput-root': {
      borderRadius: 2.5,
      backgroundColor: '#ffffff',
    },
    '& .MuiInputLabel-root': {
      fontWeight: 500,
    },
    '& .MuiFormHelperText-root': {
      marginLeft: 0.25,
    },
  },
};

const tableContainerSx = {
  borderRadius: 3,
  border: '1px solid #e2e8f0',
  boxShadow: 'none',
  overflow: 'hidden',
  backgroundColor: '#ffffff',
  '& .MuiTableHead-root .MuiTableCell-root': {
    backgroundColor: '#f8fafc',
    color: '#475569',
    fontWeight: 700,
    borderBottom: '1px solid #e2e8f0',
  },
  '& .MuiTableBody-root .MuiTableCell-root': {
    borderBottom: '1px solid #eef2f7',
    verticalAlign: 'middle',
  },
};

const dialogActionsSx = {
  px: { xs: 2, md: 3 },
  py: 2,
  gap: 1,
  borderTop: '1px solid #e5e7eb',
  backgroundColor: 'rgba(255,255,255,0.94)',
  backdropFilter: 'blur(10px)',
  justifyContent: 'space-between',
  flexWrap: 'wrap',
};

const infoAlertSx = {
  py: 0.5,
  borderRadius: 2.5,
  backgroundColor: '#eff6ff',
  border: '1px solid #bfdbfe',
  '& .MuiAlert-icon': {
    color: '#2563eb',
  },
};

interface RecetaDetailProps {
  open: boolean;
  recipeId: string;
  onClose: () => void;
  onCreateOrder?: (recipe: Recipe, options?: { qty?: number; autoCreate?: boolean }) => void;
}

export default function RecetaDetail({ open, recipeId, onClose, onCreateOrder }: RecetaDetailProps) {
  const navigate = useNavigate();
  const { t } = useTranslation(['productions', 'common']);
  const can = usePermission();
  const { config } = useCompanyConfig();
  const canWrite = can('manufacturing:update');
  const { units } = useUnits();
  const { success: toastSuccess, error: toastError } = useToast();
  const aiOptimizationEnabled = config?.features?.copilot_enabled !== false;

  const [loading, setLoading] = useState(true);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [orderPromptOpen, setOrderPromptOpen] = useState(false);
  const [customOrderQty, setCustomOrderQty] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [yieldQtyDraft, setYieldQtyDraft] = useState<number | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [costDrivers, setCostDrivers] = useState<CostDriver[]>([]);
  const [costLinesDraft, setCostLinesDraft] = useState<Array<{
    id?: string;
    driver_id: string;
    qty_standard: number;
    headcount: number;
    rate_override: number | null;
    notes?: string;
    line_order?: number;
    _isNew?: boolean;
  }>>([]);
  const [deletedCostLineIds, setDeletedCostLineIds] = useState<string[]>([]);
  const [fullCost, setFullCost] = useState<FullCostSummary | null>(null);
  const [optimizerOpen, setOptimizerOpen] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizerError, setOptimizerError] = useState<string | null>(null);
  const [optimizerResult, setOptimizerResult] = useState<RecipeOptimizationResponse | null>(null);
  const [optimizerConstraints, setOptimizerConstraints] = useState('');
  const [optimizerTargetMargin, setOptimizerTargetMargin] = useState<string>('');
  const [optimizerSellingPrice, setOptimizerSellingPrice] = useState<string>('');
  const [optimizerMaxChanges, setOptimizerMaxChanges] = useState<string>('3');
  const [optimizerLockedIds, setOptimizerLockedIds] = useState<string[]>([]);
  const [prodParams, setProdParams] = useState({
    prep_time_minutes: null as number | null,
    baking_time_minutes: null as number | null,
    oven_temp_celsius: null as number | null,
    rest_time_minutes: null as number | null,
    touch_minutes_standard: null as number | null,
    oven_minutes_standard: null as number | null,
    process_minutes: null as number | null,
    waste_pct: null as number | null,
    overhead_pct: null as number | null,
    trays_per_batch: null as number | null,
    units_per_tray: null as number | null,
    instructions: '' as string,
  });
  const [ingredientsDraft, setIngredientsDraft] = useState<Array<{
    id?: string;
    product_id: string;
    qty: number;
    unit: string;
    purchase_packaging: string;
    qty_per_package: number;
    package_unit: string;
    package_cost: number;
    notes?: string;
    line_order?: number;
    _isNew?: boolean;
  }>>([]);
  const [ingredientInsightOpen, setIngredientInsightOpen] = useState(false);
  const [ingredientInsightLoading, setIngredientInsightLoading] = useState(false);
  const [ingredientInsightError, setIngredientInsightError] = useState<string | null>(null);
  const [ingredientInsightMeta, setIngredientInsightMeta] = useState<IngredientInsightMeta | null>(null);
  const [ingredientInsightRow, setIngredientInsightRow] = useState<IngredientMasterRow | null>(null);
  const [ingredientCatalogRows, setIngredientCatalogRows] = useState<IngredientMasterRow[] | null>(null);

  useEffect(() => {
    if (open && recipeId) {
      setActiveTab(0);
      loadData();
    }
  }, [open, recipeId]);

  useEffect(() => {
    closeIngredientInsight();
  }, [recipeId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [recipeData, breakdownData] = await Promise.all([
        getRecipe(recipeId),
        getCostBreakdown(recipeId)
      ]);

      setRecipe(recipeData);
      setBreakdown(breakdownData);
      setYieldQtyDraft(Number(recipeData.yield_qty || 1));
      const recipeIngredients = Array.isArray(recipeData.ingredients) ? recipeData.ingredients : [];
      const seenProductIds = new Set<string>();
      setIngredientsDraft(
        recipeIngredients
          .filter((ing: RecipeIngredientResponse) => {
            const pid = String(ing.product_id || '');
            if (!pid || seenProductIds.has(pid)) return false;
            seenProductIds.add(pid);
            return true;
          })
          .map((ing: RecipeIngredientResponse, idx: number) => ({
            id: ing.id,
            product_id: String(ing.product_id || ''),
            qty: Number(ing.qty || 0),
            unit: normalizeUnitCode(ing.unit, units),
            purchase_packaging: String(ing.purchase_packaging || ''),
            qty_per_package: Math.max(Number(ing.qty_per_package || 1), 0.0001),
            package_unit: normalizeUnitCode(ing.package_unit, units),
            package_cost: Number(ing.package_cost || 0),
            notes: ing.notes || '',
            line_order: typeof ing.line_order === 'number' ? ing.line_order : idx,
          }))
      );
      setProdParams({
        prep_time_minutes: recipeData.prep_time_minutes ?? null,
        baking_time_minutes: recipeData.baking_time_minutes ?? null,
        oven_temp_celsius: recipeData.oven_temp_celsius ?? null,
        rest_time_minutes: recipeData.rest_time_minutes ?? null,
        touch_minutes_standard: recipeData.touch_minutes_standard ?? null,
        oven_minutes_standard: recipeData.oven_minutes_standard ?? null,
        process_minutes: recipeData.process_minutes ?? null,
        waste_pct: recipeData.waste_pct ?? null,
        overhead_pct: recipeData.overhead_pct ?? 5,
        trays_per_batch: recipeData.trays_per_batch ?? null,
        units_per_tray: recipeData.units_per_tray ?? null,
        instructions: recipeData.instructions || '',
      });
      setIsEditing(false);

      const [productsData, driversData, costLinesData, fullCostData] = await Promise.all([
        listProducts({ limit: 500 }),
        listCostDrivers().catch(() => []),
        listRecipeCostLines(recipeId).catch(() => []),
        getRecipeFullCost(recipeId).catch(() => null),
      ]);
      setProducts(Array.isArray(productsData) ? productsData : []);
      const productList = Array.isArray(productsData) ? productsData : [];
      setCostDrivers(Array.isArray(driversData) ? driversData : []);
      setCostLinesDraft(
        (Array.isArray(costLinesData) ? costLinesData : []).map((cl: RecipeCostLine, idx: number) => ({
          id: cl.id,
          driver_id: cl.driver_id,
          qty_standard: Number(cl.qty_standard || 0),
          headcount: cl.headcount || 1,
          rate_override: cl.rate_override,
          notes: cl.notes || '',
          line_order: cl.line_order ?? idx,
        }))
      );
      setDeletedCostLineIds([]);
      setFullCost(fullCostData);
      const recipeProduct = productList.find((item) => item.id === recipeData.product_id);
      setOptimizerSellingPrice(
        recipeProduct?.price != null && Number.isFinite(Number(recipeProduct.price))
          ? String(Number(recipeProduct.price))
          : ''
      );
      setOptimizerTargetMargin('');
      setOptimizerConstraints('');
      setOptimizerLockedIds([]);
      setOptimizerMaxChanges('3');
      setOptimizerError(null);
      setOptimizerResult(null);
    } catch (err: any) {
      setError(err.message || t('productions:recipe.errorLoading'));
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProductPrice = async (multiplier: number = 2.5) => {
    if (!canWrite || !recipe || !breakdown) return;

    try {
      setUpdating(true);
      const unitCost = Number(breakdown.costo_por_unidad ?? 0);
      const newPrice = unitCost * multiplier;

      await tenantApi.put(`/api/v1/tenant/products/${recipe.product_id}`, {
        price: Number(newPrice.toFixed(2)),
        cost_price: Number(unitCost.toFixed(4))
      });

      toastSuccess(`${t('productions:recipe.priceUpdated')} $${newPrice.toFixed(2)} (${t('productions:recipe.margin')} ${((multiplier - 1) * 100).toFixed(0)}%)`);
    } catch (err: any) {
      toastError(`${t('productions:recipe.errorUpdatingPrice')}: ` + (err.message || 'Unknown error'));
    } finally {
      setUpdating(false);
    }
  };

  const setIngredientField = (index: number, field: string, value: any) => {
    setIngredientsDraft((prev) => {
      const next = [...prev];
      const normalizedValue =
        field === 'unit' || field === 'package_unit'
          ? normalizeUnitCode(value, units)
          : value;
      (next[index] as any)[field] = normalizedValue;
      if (field === 'product_id') {
        const p = products.find((x) => x.id === value);
        if (p) {
          next[index].unit = normalizeUnitCode(p.unit, units);
          next[index].package_unit = normalizeUnitCode(p.unit, units);
        }
      }
      return next;
    });
  };

  const addNewIngredientRow = () => {
    if (!isEditing) setIsEditing(true);
    setIngredientsDraft((prev) => [
      ...prev,
      {
        product_id: '',
        qty: 1,
        unit: 'uds',
        purchase_packaging: '',
        qty_per_package: 1,
        package_unit: 'uds',
        package_cost: 0,
        line_order: prev.length,
        _isNew: true,
      },
    ]);
  };

  const removeIngredientRow = (index: number) => {
    setIngredientsDraft((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSaveIngredients = async () => {
    if (!canWrite || !recipe) return;
    try {
      setUpdating(true);
      setError(null);

      const normalizedYieldQty = Math.floor(Number(yieldQtyDraft || 0));
      if (!Number.isFinite(normalizedYieldQty) || normalizedYieldQty <= 0) {
        setError('El rendimiento debe ser mayor que 0');
        return;
      }

      const normalizedIngredients = ingredientsDraft
        .filter((row) => row.product_id && Number(row.qty || 0) > 0)
        .map((row, index) => ({
          product_id: row.product_id,
          qty: Number(row.qty || 0),
          unit: normalizeUnitCode(row.unit, units),
          purchase_packaging: String(row.purchase_packaging || '-'),
          qty_per_package: Math.max(Number(row.qty_per_package || 1), 0.0001),
          package_unit: normalizeUnitCode(row.package_unit || row.unit, units),
          package_cost: Number(row.package_cost || 0),
          notes: row.notes || undefined,
          line_order: index,
        }));

      const seenProducts = new Set<string>();
      for (const ingredient of normalizedIngredients) {
        if (seenProducts.has(ingredient.product_id)) {
          const productName = products.find((item) => item.id === ingredient.product_id)?.name;
          setError(productName ? `El ingrediente ${productName} ya existe en la receta.` : 'El ingrediente ya existe en la receta.');
          return;
        }
        seenProducts.add(ingredient.product_id);
      }

      await updateRecipe(recipe.id, {
        yield_qty: normalizedYieldQty,
        prep_time_minutes: prodParams.prep_time_minutes ?? undefined,
        baking_time_minutes: prodParams.baking_time_minutes ?? undefined,
        oven_temp_celsius: prodParams.oven_temp_celsius ?? undefined,
        rest_time_minutes: prodParams.rest_time_minutes ?? undefined,
        touch_minutes_standard: prodParams.touch_minutes_standard ?? 0,
        oven_minutes_standard: prodParams.oven_minutes_standard ?? 0,
        process_minutes: Math.max((prodParams.prep_time_minutes || 0) - (prodParams.touch_minutes_standard || 0), 0) || undefined,
        waste_pct: prodParams.waste_pct ?? undefined,
        overhead_pct: prodParams.overhead_pct ?? undefined,
        trays_per_batch: (prodParams.trays_per_batch && prodParams.trays_per_batch >= 1) ? prodParams.trays_per_batch : undefined,
        units_per_tray: (prodParams.units_per_tray && prodParams.units_per_tray >= 1) ? prodParams.units_per_tray : undefined,
        instructions: prodParams.instructions || undefined,
        ingredients: normalizedIngredients,
      });

      // Save cost lines
      for (const clId of deletedCostLineIds) {
        await deleteRecipeCostLine(recipe.id, clId);
      }
      const laborMinutesForSave = prodParams.touch_minutes_standard ?? prodParams.prep_time_minutes ?? 0;
      const laborHoursForSave = laborMinutesForSave / 60;

      for (const cl of costLinesDraft) {
        if (!cl.driver_id) continue;
        const driver = costDrivers.find((d) => d.id === cl.driver_id);
        const isLaborAutoSave = isLaborAutoDriver(driver);
        const isOvenAutoSave = driver && !isLaborAutoSave && (driver.consumption_rate ?? 0) > 0;
        const ovenMinutesForSave = prodParams.baking_time_minutes ?? 0;
        const ovenAutoQtyForSave = isOvenAutoSave && ovenMinutesForSave > 0
          ? (ovenMinutesForSave / 60) * (driver!.consumption_rate ?? 0)
          : null;
        const qtyToSave = isLaborAutoSave && laborHoursForSave > 0
          ? laborHoursForSave
          : ovenAutoQtyForSave !== null
            ? ovenAutoQtyForSave
            : Number(cl.qty_standard || 0);

        const clPayload = {
          driver_id: cl.driver_id,
          qty_standard: qtyToSave,
          headcount: cl.headcount || 1,
          rate_override: cl.rate_override ?? undefined,
          notes: cl.notes || undefined,
          line_order: cl.line_order || 0,
        };
        if (cl._isNew || !cl.id) {
          await addRecipeCostLine(recipe.id, clPayload as any);
        } else {
          await updateRecipeCostLine(recipe.id, cl.id, clPayload as any);
        }
      }

      await loadData();
      setIsEditing(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map((d: any) => `${(d.loc || []).join('.')}: ${d.msg}`).join('; ')
        : err?.message || t('productions:recipe.errorSavingIngredients');
      setError(msg);
    } finally {
      setUpdating(false);
    }
  };

  const closeIngredientInsight = () => {
    setIngredientInsightOpen(false);
    setIngredientInsightLoading(false);
    setIngredientInsightError(null);
    setIngredientInsightRow(null);
    setIngredientInsightMeta(null);
  };

  const openIngredientInsight = async (
    item: {
      product_id: string;
      qty: number;
      unit: string;
      package_unit: string;
      qty_per_package: number;
      package_cost: number;
    },
    productName: string,
  ) => {
    const qtyInPackageUnit = convertQtyToUnit(
      Number(item.qty || 0),
      item.unit,
      item.package_unit || item.unit,
    );
    const estimatedCost =
      (qtyInPackageUnit / Math.max(Number(item.qty_per_package || 1), 0.0001)) *
      Number(item.package_cost || 0);

    setIngredientInsightMeta({
      productId: item.product_id,
      productName,
      recipeQtyLabel: `${Number(item.qty || 0).toFixed(2)} ${item.unit || ''}`.trim(),
      recipeQtyReference: formatIngredientReference(Number(item.qty || 0), item.unit, units),
      estimatedCost,
    });
    setIngredientInsightRow(null);
    setIngredientInsightError(null);
    setIngredientInsightOpen(true);
    setIngredientInsightLoading(true);

    try {
      const rows = ingredientCatalogRows ?? await fetchIngredientMasterRows();
      if (!ingredientCatalogRows) {
        setIngredientCatalogRows(rows);
      }
      setIngredientInsightRow(rows.find((row) => row.product_id === item.product_id) ?? null);
    } catch (err: any) {
      setIngredientInsightError(err?.message || 'No se pudo cargar la ficha del ingrediente');
    } finally {
      setIngredientInsightLoading(false);
    }
  };

  const openIngredientMasterPage = () => {
    if (!ingredientInsightMeta?.productId) return;
    const params = new URLSearchParams({ productId: ingredientInsightMeta.productId });
    closeIngredientInsight();
    navigate(`../ingredientes?${params.toString()}`);
  };

  const openRecipeFromIngredientInsight = (targetRecipeId: string) => {
    closeIngredientInsight();
    navigate(`../recetas/${targetRecipeId}`);
  };

  const openOrderPrompt = () => {
    if (!canWrite) return;
    const baseQty = Number(recipe?.yield_qty || 1);
    setCustomOrderQty(String(baseQty > 0 ? baseQty : 1));
    setOrderPromptOpen(true);
  };

  const submitOrderWithQty = (qty: number) => {
    if (!canWrite || !recipe || !onCreateOrder) return;
    const safeQty = Number.isFinite(qty) && qty > 0 ? qty : Number(recipe.yield_qty || 1);
    onCreateOrder(recipe, { qty: safeQty, autoCreate: true });
    setOrderPromptOpen(false);
  };

  const startInlineEdit = () => {
    if (!canWrite) return;
    if (!isEditing) setIsEditing(true);
  };

  const handleCancelEditing = () => {
    void loadData();
  };

  const openOptimizer = () => {
    if (!aiOptimizationEnabled || !recipe) return;
    setOptimizerError(null);
    setOptimizerResult(null);
    setOptimizerLockedIds([]);
    setOptimizerOpen(true);
  };

  const closeOptimizer = () => {
    if (optimizing) return;
    setOptimizerOpen(false);
    setOptimizerError(null);
  };

  const toggleLockedIngredient = (productId: string) => {
    setOptimizerLockedIds((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    );
  };

  const handleRunOptimization = async () => {
    if (!recipe) return;
    try {
      setOptimizing(true);
      setOptimizerError(null);
      const sellingPrice = optimizerSellingPrice.trim() === '' ? null : Number(optimizerSellingPrice);
      const targetMargin = optimizerTargetMargin.trim() === '' ? null : Number(optimizerTargetMargin);
      const maxChanges = Number(optimizerMaxChanges || 3);

      const result = await optimizeRecipe(recipe.id, {
        selling_price: sellingPrice,
        target_margin_pct: targetMargin,
        max_ingredients_to_change: Number.isFinite(maxChanges) && maxChanges > 0 ? maxChanges : 3,
        locked_product_ids: optimizerLockedIds,
        constraints: optimizerConstraints.trim() || null,
      });

      setOptimizerResult(result);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setOptimizerError(typeof detail === 'string' ? detail : (err?.message || 'No se pudo optimizar la receta.'));
    } finally {
      setOptimizing(false);
    }
  };

  const handleApplyOptimization = async () => {
    if (!canWrite || !recipe || !optimizerResult) return;
    try {
      setOptimizing(true);
      setOptimizerError(null);
      await updateRecipe(recipe.id, optimizerResult.optimized_recipe);
      await loadData();
      setOptimizerOpen(false);
      toastSuccess('Propuesta optimizada aplicada a la receta.');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setOptimizerError(typeof detail === 'string' ? detail : (err?.message || 'No se pudo aplicar la propuesta.'));
    } finally {
      setOptimizing(false);
    }
  };

  if (loading) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogContent>
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        </DialogContent>
      </Dialog>
    );
  }

  if (error || !recipe || !breakdown) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogContent>
          <Alert severity="error">{error || t('productions:recipe.errorLoading')}</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t('productions:recipe.close')}</Button>
        </DialogActions>
      </Dialog>
    );
  }

  const ingredientsCount = Number(breakdown.ingredientes_count ?? 0);
  const breakdownRows = Array.isArray(breakdown.desglose) ? breakdown.desglose : [];

  // Recalculate materials cost on the frontend with correct unit conversion
  // (backend formula lacks g→kg / oz→lb etc. conversion)
  const correctedMaterials = ingredientsDraft.reduce((sum, item) => {
    const qtyConverted = convertQtyToUnit(
      Number(item.qty || 0),
      item.unit,
      item.package_unit || item.unit,
    )
    return sum + (qtyConverted / Math.max(Number(item.qty_per_package || 1), 0.0001)) * Number(item.package_cost || 0)
  }, 0)

  const yieldQty = Number(recipe.yield_qty || 1)
  const totalCost = correctedMaterials
  const unitCost = yieldQty > 0 ? correctedMaterials / yieldQty : 0

  const fc = fullCost;

  // Recalculate waste/overhead based on corrected materials
  const correctedWastePct  = Number(recipe.waste_pct   || fc?.waste_pct    || 0)
  const correctedOverPct   = Number(recipe.overhead_pct || fc?.overhead_pct || 0)
  const correctedWaste     = correctedMaterials * (correctedWastePct  / 100)
  const correctedOverhead  = correctedMaterials * (correctedOverPct   / 100)
  const correctedFullTotal = correctedMaterials + correctedWaste + correctedOverhead + Number(fc?.indirect_total || 0)
  const correctedFullUnit  = yieldQty > 0 ? correctedFullTotal / yieldQty : 0

  const hasIndirect = fc && (
    Number(fc.indirect_total || 0) > 0 ||
    correctedWaste > 0 ||
    correctedOverhead > 0
  );
  const tabFallback = (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
      <CircularProgress size={24} />
    </Box>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: dialogPaperSx }}>
      {/* ── Header: título + métricas clave + pestañas ── */}
      <DialogTitle
        component="div"
        sx={{
          px: { xs: 2, md: 3 },
          pt: { xs: 1.5, md: 2 },
          pb: 0,
          borderBottom: '1px solid #e5e7eb',
          backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5, gap: 2 }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h6" component="h2" sx={{ fontWeight: 700, lineHeight: 1.3 }}>
              {recipe.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
              {recipe.product_name}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2, flexShrink: 0, textAlign: 'right', pt: 0.25 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.2 }}>Rendimiento</Typography>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{recipe.yield_qty} uds</Typography>
            </Box>
            <Box sx={{ borderLeft: '1px solid #e2e8f0', pl: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.2 }}>Costo / u</Typography>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                ${(correctedFullUnit > 0 ? correctedFullUnit : unitCost).toFixed(4)}
              </Typography>
            </Box>
          </Box>
        </Box>
        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v as number)}
          sx={{
            minHeight: 38,
            '& .MuiTab-root': { minHeight: 38, fontSize: '0.78rem', fontWeight: 600, px: 2, py: 0.75, textTransform: 'none' },
            '& .MuiTabs-indicator': { backgroundColor: '#2563eb', height: 2.5 },
          }}
        >
          <Tab label="Resumen" />
          <Tab label={ingredientsDraft.length > 0 ? `Ingredientes (${ingredientsDraft.length})` : 'Ingredientes'} />
          <Tab label="Parámetros" />
          <Tab label="Costos Ind." />
        </Tabs>
      </DialogTitle>

      <DialogContent
        sx={{
          px: { xs: 2, md: 3 },
          py: { xs: 2, md: 2.5 },
          borderColor: '#e5e7eb',
          backgroundColor: '#f8fafc',
          minHeight: 320,
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2.5 }}>{error}</Alert>
        )}
        {isEditing && (
          <Alert severity="info" sx={{ ...infoAlertSx, mb: 2 }}>
            Modo edición activo — navega entre pestañas para editar cada sección.
          </Alert>
        )}

        {/* ── Pestaña 0: Resumen ── */}
        {activeTab === 0 && (
          <Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} sm={3}>
                <Box sx={metricCardSx}>
                  <Typography variant="caption" color="text.secondary">Rendimiento</Typography>
                  {isEditing ? (
                    <TextField
                      type="number"
                      size="small"
                      fullWidth
                      value={yieldQtyDraft ?? ''}
                      onChange={(e) => setYieldQtyDraft(e.target.value ? Number(e.target.value) : null)}
                      inputProps={{ min: 1, step: 1 }}
                      helperText="Uds producidas"
                      sx={{ mt: 0.5 }}
                    />
                  ) : (
                    <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>{recipe.yield_qty} uds</Typography>
                  )}
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={metricCardSx}>
                  <Typography variant="caption" color="text.secondary">Materiales (lote)</Typography>
                  <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>${correctedMaterials.toFixed(2)}</Typography>
                  <Typography variant="caption" color="text.secondary">/u: ${unitCost.toFixed(4)}</Typography>
                </Box>
              </Grid>
              {hasIndirect ? (
                <>
                  <Grid item xs={6} sm={3}>
                    <Box sx={metricCardSx}>
                      <Typography variant="caption" color="text.secondary">Costo total (lote)</Typography>
                      <Typography variant="h6" color="error.main" sx={{ mt: 0.5, fontWeight: 700 }}>${correctedFullTotal.toFixed(2)}</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Box sx={metricCardSx}>
                      <Typography variant="caption" color="text.secondary">Costo / unidad</Typography>
                      <Typography variant="h6" color="error.main" sx={{ mt: 0.5, fontWeight: 700 }}>${correctedFullUnit.toFixed(4)}</Typography>
                    </Box>
                  </Grid>
                </>
              ) : (
                <>
                  <Grid item xs={6} sm={3}>
                    <Box sx={metricCardSx}>
                      <Typography variant="caption" color="text.secondary">Costo / unidad</Typography>
                      <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>${unitCost.toFixed(4)}</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Box sx={metricCardSx}>
                      <Typography variant="caption" color="text.secondary">Ingredientes</Typography>
                      <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>{ingredientsCount}</Typography>
                    </Box>
                  </Grid>
                </>
              )}
            </Grid>

            {hasIndirect && fc && (
              <Box sx={{ border: '1px solid #e2e8f0', borderRadius: 2, overflow: 'hidden' }}>
                <Box sx={{ px: 2, py: 0.75, background: '#f1f5f9', borderBottom: '1px solid #e2e8f0' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: '#475569', letterSpacing: 0.8 }}>
                    DESGLOSE — {recipe.yield_qty} unidades
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9' }}>
                  <Typography variant="body2" color="text.secondary">Materiales</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>${correctedMaterials.toFixed(2)}</Typography>
                </Box>
                {correctedWaste > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9', background: '#fff7ed' }}>
                    <Typography variant="body2" color="warning.dark">Merma ({fc.waste_pct}%)</Typography>
                    <Typography variant="body2" color="warning.dark" sx={{ fontWeight: 600 }}>${correctedWaste.toFixed(2)}</Typography>
                  </Box>
                )}
                {correctedOverhead > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9', background: '#f0fdf4' }}>
                    <Typography variant="body2" color="success.dark">Depreciación ({fc.overhead_pct}%)</Typography>
                    <Typography variant="body2" color="success.dark" sx={{ fontWeight: 600 }}>${correctedOverhead.toFixed(2)}</Typography>
                  </Box>
                )}
                {Number(fc.labor_with_burden_factor || fc.labor_total || 0) > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9' }}>
                    <Typography variant="body2" color="text.secondary">Mano de obra</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>${Number(fc.labor_with_burden_factor || fc.labor_total).toFixed(2)}</Typography>
                  </Box>
                )}
                {(Number(fc.electricity_total || 0) + Number(fc.diesel_total || 0)) > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9' }}>
                    <Typography variant="body2" color="text.secondary">Energía / Combustible</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>${(Number(fc.electricity_total || 0) + Number(fc.diesel_total || 0)).toFixed(2)}</Typography>
                  </Box>
                )}
                {Number(fc.other_indirect_total || 0) > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, borderBottom: '1px solid #f1f5f9' }}>
                    <Typography variant="body2" color="text.secondary">Otros indirectos</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>${Number(fc.other_indirect_total).toFixed(2)}</Typography>
                  </Box>
                )}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, background: '#1e293b' }}>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: '#f8fafc' }}>TOTAL ({recipe.yield_qty} uds)</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: '#fbbf24' }}>${correctedFullTotal.toFixed(2)}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.6, background: '#0f172a' }}>
                  <Typography variant="caption" sx={{ color: '#94a3b8' }}>Por unidad</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: '#34d399' }}>${correctedFullUnit.toFixed(4)} / u</Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}

        {/* ── Pestaña 1: Ingredientes ── */}
        {activeTab === 1 && (
          <React.Suspense fallback={tabFallback}>
            <RecetaIngredientsTab
              t={t}
              isEditing={isEditing}
              ingredientsDraft={ingredientsDraft}
              products={products}
              units={units}
              totalCost={totalCost}
              tableContainerSx={tableContainerSx}
              onAddIngredient={addNewIngredientRow}
              onSetIngredientField={setIngredientField}
              onRemoveIngredient={removeIngredientRow}
              onOpenIngredientInsight={openIngredientInsight}
            />
          </React.Suspense>
        )}

        {/* Parametros de produccion */}
        {activeTab === 2 && recipe && (
          <React.Suspense fallback={tabFallback}>
            <RecetaParametersTab
              t={t}
              isEditing={isEditing}
              recipe={recipe}
              prodParams={prodParams}
              fieldGroupSx={fieldGroupSx}
              infoAlertSx={infoAlertSx}
              onSetProdParams={setProdParams}
            />
          </React.Suspense>
        )}

        {/* Costos indirectos */}
        {activeTab === 3 && (
          <React.Suspense fallback={tabFallback}>
            <RecetaCostsTab
              t={t}
              isEditing={isEditing}
              costDrivers={costDrivers}
              costLinesDraft={costLinesDraft}
              prodParams={prodParams}
              infoAlertSx={infoAlertSx}
              tableContainerSx={tableContainerSx}
              normalizeCostDriverUnit={normalizeCostDriverUnit}
              isLaborAutoDriver={isLaborAutoDriver}
              onSetCostLinesDraft={setCostLinesDraft}
              onSetDeletedCostLineIds={setDeletedCostLineIds}
            />
          </React.Suspense>
        )}
      </DialogContent>

      <DialogActions sx={dialogActionsSx}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {isEditing ? (
            <>
              <Button
                variant="text"
                onClick={handleCancelEditing}
                disabled={updating}
                sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}
              >
                Cancelar
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSaveIngredients}
                disabled={updating}
                sx={{ minWidth: 140, borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
              >
                {updating ? <CircularProgress size={16} color="inherit" /> : 'Guardar cambios'}
              </Button>
            </>
          ) : (
            canWrite && (
              <Button
                variant="outlined"
                onClick={startInlineEdit}
                sx={{ borderRadius: 2.5, fontWeight: 600 }}
              >
                Editar receta
              </Button>
            )
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {canWrite && onCreateOrder && recipe && !isEditing && (
            <Button
              variant="contained"
              color="primary"
              onClick={openOrderPrompt}
              disabled={updating}
              sx={{ borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
            >
              {t('productions:recipe.newOrder')}
            </Button>
          )}
          {aiOptimizationEnabled && recipe && !isEditing && (
            <Button
              variant="outlined"
              color="secondary"
              onClick={openOptimizer}
              disabled={updating}
              startIcon={<AutoFixHigh />}
              sx={{ borderRadius: 2.5, fontWeight: 700 }}
            >
              Optimizar con IA
            </Button>
          )}
          <Button onClick={onClose} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>{t('productions:recipe.close')}</Button>
        </Box>
      </DialogActions>

      <React.Suspense fallback={null}>
        <RecetaIngredientInsightDialog
          open={ingredientInsightOpen}
          loading={ingredientInsightLoading}
          error={ingredientInsightError}
          meta={ingredientInsightMeta}
          row={ingredientInsightRow}
          onClose={closeIngredientInsight}
          onOpenIngredientMaster={openIngredientMasterPage}
          onOpenRecipe={openRecipeFromIngredientInsight}
          dialogPaperSx={dialogPaperSx}
          dialogActionsSx={dialogActionsSx}
          sectionCardSx={sectionCardSx}
        />
      </React.Suspense>

      <React.Suspense fallback={null}>
        <RecetaOptimizerDialog
          open={aiOptimizationEnabled && optimizerOpen}
          canWrite={canWrite}
          optimizing={optimizing}
          optimizerError={optimizerError}
          optimizerResult={optimizerResult}
          optimizerSellingPrice={optimizerSellingPrice}
          optimizerTargetMargin={optimizerTargetMargin}
          optimizerMaxChanges={optimizerMaxChanges}
          optimizerConstraints={optimizerConstraints}
          optimizerLockedIds={optimizerLockedIds}
          ingredientsDraft={ingredientsDraft}
          products={products}
          onChangeSellingPrice={setOptimizerSellingPrice}
          onChangeTargetMargin={setOptimizerTargetMargin}
          onChangeMaxChanges={setOptimizerMaxChanges}
          onChangeConstraints={setOptimizerConstraints}
          onToggleLockedIngredient={toggleLockedIngredient}
          onClose={closeOptimizer}
          onRun={handleRunOptimization}
          onApply={handleApplyOptimization}
          dialogPaperSx={dialogPaperSx}
          dialogActionsSx={dialogActionsSx}
          sectionCardSx={sectionCardSx}
          metricCardSx={metricCardSx}
          tableContainerSx={tableContainerSx}
        />
      </React.Suspense>

      <Dialog open={canWrite && orderPromptOpen} onClose={() => setOrderPromptOpen(false)} maxWidth="xs" fullWidth PaperProps={{ sx: dialogPaperSx }}>
        <DialogTitle sx={{ px: 3, py: 2.5, borderBottom: '1px solid #e5e7eb', backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)' }}>
          {t('productions:recipe.createOrder')}
        </DialogTitle>
        <DialogContent sx={{ px: 3, py: 3, backgroundColor: '#f8fafc' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('productions:recipe.useRecipeQty')}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {t('productions:recipe.recipeYield')}: <strong>{recipe?.yield_qty || 0}</strong>
          </Typography>
          <TextField
            label={t('productions:recipe.otherQty')}
            type="number"
            fullWidth
            value={customOrderQty}
            onChange={(e) => setCustomOrderQty(e.target.value)}
            inputProps={{ min: 0.01, step: 0.01 }}
            sx={{ mb: 2 }}
          />
          <Typography variant="body2" color="text.secondary">
            {t('productions:recipe.estimatedCost')}:{' '}
            <strong>
              ${(Number(breakdown?.costo_por_unidad || 0) * Math.max(Number(customOrderQty || 0), 0)).toFixed(2)}
            </strong>
          </Typography>
        </DialogContent>
        <DialogActions sx={dialogActionsSx}>
          <Button onClick={() => setOrderPromptOpen(false)} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>{t('common:actions.cancel')}</Button>
          <Button
            variant="outlined"
            onClick={() => submitOrderWithQty(Number(recipe?.yield_qty || 1))}
            sx={{ borderRadius: 2.5, fontWeight: 600 }}
          >
            {t('productions:recipe.sameQty')}
          </Button>
          <Button
            variant="contained"
            onClick={() => submitOrderWithQty(Number(customOrderQty))}
            disabled={!Number(customOrderQty) || Number(customOrderQty) <= 0}
            sx={{ borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
          >
            {t('productions:recipe.useThisQty')}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}
