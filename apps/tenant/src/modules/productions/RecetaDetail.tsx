/**
 * RecetaDetail - Vista detallada de receta con desglose de costos
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Typography, Box, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Alert, CircularProgress, Grid,
  TextField, IconButton, Tabs, Tab
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import {
  getRecipe,
  getCostBreakdown,
  updateRecipe,
  type Recipe,
  type CostBreakdown,
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
import { useToast } from '../../shared/toast';
import { useUnits } from '../../hooks/useUnits';
import { normalizeUnitCode, convertQtyToUnit } from '../../services/unitService';

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
  const { t } = useTranslation(['productions', 'common']);
  const can = usePermission();
  const canWrite = can('produccion:write');
  const { units } = useUnits();
  const { success: toastSuccess, error: toastError } = useToast();

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

  useEffect(() => {
    if (open && recipeId) {
      setActiveTab(0);
      loadData();
    }
  }, [open, recipeId]);

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
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#334155' }}>
                Ingredientes de la receta
              </Typography>
              {isEditing && (
                <Button size="small" startIcon={<Add />} onClick={addNewIngredientRow} sx={{ borderRadius: 2.5, fontWeight: 600 }}>
                  {t('productions:recipe.addIngredient')}
                </Button>
              )}
            </Box>
            <TableContainer component={Paper} variant="outlined" sx={tableContainerSx}>
              <Table size="small">
                <TableHead>
                  {isEditing ? (
                    <>
                      <TableRow>
                        <TableCell rowSpan={2}>{t('productions:recipe.ingredients')}</TableCell>
                        <TableCell colSpan={2} align="center">Uso receta</TableCell>
                        <TableCell rowSpan={2} align="right">Kg / Lb</TableCell>
                        <TableCell rowSpan={2} align="right">{t('productions:recipe.cost')}</TableCell>
                        <TableCell rowSpan={2} align="right">%</TableCell>
                        <TableCell rowSpan={2} />
                      </TableRow>
                      <TableRow>
                        <TableCell align="right">{t('productions:recipe.quantity')}</TableCell>
                        <TableCell>Unidad</TableCell>
                      </TableRow>
                    </>
                  ) : (
                    <TableRow>
                      <TableCell>{t('productions:recipe.ingredients')}</TableCell>
                      <TableCell align="right">{t('productions:recipe.quantity')}</TableCell>
                      <TableCell align="right">Kg / Lb</TableCell>
                      <TableCell align="right">{t('productions:recipe.cost')}</TableCell>
                      <TableCell align="right">%</TableCell>
                    </TableRow>
                  )}
                </TableHead>
                <TableBody>
                  {ingredientsDraft.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={isEditing ? 7 : 5} align="center">
                        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                          {t('productions:recipe.noIngredients')}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                  {ingredientsDraft.map((item, index) => {
                    const product = products.find((p) => p.id === item.product_id);
                    const productName = product?.name || (item as any)?.product_name || '-';
                    const qty = Number(item.qty ?? 0);
                    const unitNorm = normalizeUnitCode(item.unit, units);
                    let kgLbText: string | null = null;
                    if (unitNorm === 'g') {
                      const kg = qty / 1000;
                      const lb = qty / 453.592;
                      kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                    } else if (unitNorm === 'kg') {
                      const lb = qty * 2.20462;
                      kgLbText = `${qty.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                    } else if (unitNorm === 'lb') {
                      const kg = qty / 2.20462;
                      kgLbText = `${kg.toFixed(3)} kg / ${qty.toFixed(3)} lb`;
                    } else if (unitNorm === 'oz') {
                      const lb = qty / 16;
                      const kg = lb / 2.20462;
                      kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                    }
                    const qtyInPackageUnit = convertQtyToUnit(
                      Number(item.qty || 0),
                      item.unit,
                      item.package_unit || item.unit,
                    );
                    const estimatedCost =
                      (qtyInPackageUnit / Math.max(Number(item.qty_per_package || 1), 0.0001)) *
                      Number(item.package_cost || 0);
                    const pct = totalCost > 0 ? (estimatedCost / totalCost) * 100 : 0;
                    return (
                      <TableRow key={index}>
                        <TableCell>
                          {isEditing ? (
                            <TextField
                              select
                              SelectProps={{ native: true }}
                              value={item.product_id}
                              onChange={(e) => setIngredientField(index, 'product_id', e.target.value)}
                              size="small"
                              fullWidth
                            >
                              <option value="">{t('productions:recipe.selectProduct')}</option>
                              {products.map((p) => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                              ))}
                            </TextField>
                          ) : (
                            productName
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {isEditing ? (
                            <TextField
                              type="number"
                              value={item.qty}
                              onChange={(e) => setIngredientField(index, 'qty', Number(e.target.value))}
                              size="small"
                              sx={{ width: 90 }}
                            />
                          ) : (
                            `${qty.toFixed(2)} ${item.unit || ''}`
                          )}
                        </TableCell>
                        {isEditing && (
                          <TableCell>
                            <TextField
                              select
                              SelectProps={{ native: true }}
                              value={normalizeUnitCode(item.unit, units)}
                              onChange={(e) => setIngredientField(index, 'unit', e.target.value)}
                              size="small"
                              sx={{ width: 90 }}
                            >
                              {units.map((unit) => (
                                <option key={unit.code} value={unit.code}>{unit.label}</option>
                              ))}
                            </TextField>
                          </TableCell>
                        )}
                        <TableCell align="right">
                          {kgLbText ? (
                            <Typography variant="body2" color="text.secondary">{kgLbText}</Typography>
                          ) : (
                            <Typography variant="body2" color="text.secondary">-</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <strong>${estimatedCost.toFixed(2)}</strong>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${pct.toFixed(1)}%`}
                            size="small"
                            color={pct > 30 ? 'error' : pct > 15 ? 'warning' : 'default'}
                          />
                        </TableCell>
                        {isEditing && (
                          <TableCell align="right">
                            <IconButton color="error" onClick={() => removeIngredientRow(index)} size="small">
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* ── Pestaña 2: Parámetros de producción ── */}
        {activeTab === 2 && (
          <Box>
            {isEditing ? (
              <Box sx={fieldGroupSx}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {t('productions:recipe.productionParameters')}
                  </Typography>
                </Box>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.prepTime')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.prep_time_minutes ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, prep_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0 }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.bakingTime')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.baking_time_minutes ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, baking_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0 }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.ovenTemp')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.oven_temp_celsius ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, oven_temp_celsius: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0 }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.restTime')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.rest_time_minutes ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, rest_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0 }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Alert severity="info" sx={infoAlertSx}>
                      🟢 Touch = {t('productions:recipe.touchDescription')} | ⚫ {t('productions:recipe.processDescription')}
                    </Alert>
                  </Grid>
                  <Grid item xs={6} sm={6}>
                    <TextField
                      label={t('productions:recipe.activeWorkMin')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.touch_minutes_standard ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, touch_minutes_standard: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0 }}
                      helperText={t('productions:recipe.activeWorkHelper')}
                    />
                  </Grid>
                  <Grid item xs={6} sm={6}>
                    <TextField
                      label={t('productions:recipe.passiveProcess')}
                      type="number"
                      size="small"
                      fullWidth
                      value={Math.max((prodParams.prep_time_minutes || 0) - (prodParams.touch_minutes_standard || 0), 0) || ''}
                      InputProps={{ readOnly: true }}
                      inputProps={{ min: 0 }}
                      helperText={t('productions:recipe.passiveProcessHelper')}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.wastePct')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.waste_pct ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, waste_pct: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0, max: 100, step: 0.1 }}
                      helperText="Pérdida de materiales"
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label="% Depreciación"
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.overhead_pct ?? 5}
                      onChange={(e) => setProdParams((p) => ({ ...p, overhead_pct: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 0, max: 100, step: 0.1 }}
                      helperText="Amort. maquinaria (default 5%)"
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.traysPerBatch')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.trays_per_batch ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, trays_per_batch: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 1 }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <TextField
                      label={t('productions:recipe.unitsPerTray')}
                      type="number"
                      size="small"
                      fullWidth
                      value={prodParams.units_per_tray ?? ''}
                      onChange={(e) => setProdParams((p) => ({ ...p, units_per_tray: e.target.value ? Number(e.target.value) : null }))}
                      inputProps={{ min: 1 }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      label={t('productions:recipe.instructions')}
                      size="small"
                      fullWidth
                      multiline
                      minRows={2}
                      value={prodParams.instructions}
                      onChange={(e) => setProdParams((p) => ({ ...p, instructions: e.target.value }))}
                    />
                  </Grid>
                </Grid>
              </Box>
            ) : (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {t('productions:recipe.productionParameters')}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {recipe.prep_time_minutes != null && (
                    <Chip label={`⏱️ ${t('productions:recipe.prepLabel')}: ${recipe.prep_time_minutes} min`} color="primary" size="small" />
                  )}
                  {recipe.baking_time_minutes != null && (
                    <Chip label={`🔥 ${t('productions:recipe.bakingLabel')}: ${recipe.baking_time_minutes} min`} color="warning" size="small" />
                  )}
                  {recipe.oven_temp_celsius != null && (
                    <Chip label={`🌡️ ${recipe.oven_temp_celsius} °C`} color="default" size="small" />
                  )}
                  {recipe.rest_time_minutes != null && (
                    <Chip label={`⏸️ ${t('productions:recipe.restLabel')}: ${recipe.rest_time_minutes} min`} color="info" size="small" />
                  )}
                  {(recipe as any).touch_minutes_standard != null && (recipe as any).touch_minutes_standard > 0 && (
                    <Chip label={`🟢 ${t('productions:recipe.activeWorkMin')}: ${(recipe as any).touch_minutes_standard} min`} color="success" size="small" />
                  )}
                  {(recipe as any).process_minutes != null && (recipe as any).process_minutes > 0 && (
                    <Chip label={`⚫ ${t('productions:recipe.processLabel')}: ${(recipe as any).process_minutes} min`} color="default" size="small" />
                  )}
                  {recipe.waste_pct != null && recipe.waste_pct > 0 && (
                    <Chip label={`📉 ${t('productions:recipe.wasteLabel')}: ${recipe.waste_pct}%`} color="error" size="small" />
                  )}
                  {recipe.overhead_pct != null && recipe.overhead_pct > 0 && (
                    <Chip label={`🔧 Depreciación: ${recipe.overhead_pct}%`} color="warning" size="small" />
                  )}
                  {recipe.trays_per_batch != null && (
                    <Chip label={`🍞 ${recipe.trays_per_batch} ${t('productions:recipe.traysLabel')}`} color="default" size="small" />
                  )}
                  {recipe.units_per_tray != null && (
                    <Chip label={`${recipe.units_per_tray} ${t('productions:recipe.unitsPerTrayLabel')}`} color="default" size="small" />
                  )}
                </Box>
                {recipe.instructions && (
                  <Box sx={{ mt: 2, p: 2, borderRadius: 2, border: '1px solid #e2e8f0', background: '#fff' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                      {t('productions:recipe.instructions')}
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.7 }}>
                      {recipe.instructions}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}

        {/* ── Pestaña 3: Costos Indirectos ── */}
        {activeTab === 3 && (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#334155' }}>
                {t('productions:recipe.indirectCosts')}
              </Typography>
            </Box>

            {costDrivers.length === 0 && !isEditing && (
              <Alert severity="info" sx={{ ...infoAlertSx }}>
                {t('productions:recipe.noCostDriversInfo')}
              </Alert>
            )}

            {(costLinesDraft.length > 0 || isEditing) && (
              <TableContainer component={Paper} variant="outlined" sx={{ ...tableContainerSx, mb: isEditing ? 1.5 : 0 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('productions:recipe.costType')}</TableCell>
                      <TableCell align="right">{t('productions:recipe.qty')}</TableCell>
                      <TableCell align="right">{t('productions:recipe.headcount')}</TableCell>
                      <TableCell align="right">{t('productions:recipe.rate')}</TableCell>
                      <TableCell align="right">{t('productions:recipe.subtotal')}</TableCell>
                      {isEditing && <TableCell />}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {costLinesDraft.map((cl, idx) => {
                      const driver = costDrivers.find((d) => d.id === cl.driver_id);
                      const rate = cl.rate_override ?? (driver?.default_rate || 0);
                      const driverUnitNorm = normalizeCostDriverUnit(driver?.unit);
                      const isLaborAuto = isLaborAutoDriver(driver);
                      const isEnergyDriver = !!driver && !isLaborAuto && (driver.consumption_rate ?? 0) > 0;
                      const isOvenAuto = isEnergyDriver;
                      const laborMinutes = prodParams.touch_minutes_standard ?? prodParams.prep_time_minutes ?? 0;
                      const recipeLaborHours = laborMinutes / 60;
                      const laborSource = prodParams.touch_minutes_standard != null
                        ? 'touch'
                        : (prodParams.prep_time_minutes != null ? 'prep' : null);
                      const ovenMinutes = prodParams.baking_time_minutes ?? 0;
                      const ovenHours = ovenMinutes / 60;
                      const ovenAutoQty = isOvenAuto ? ovenHours * (driver!.consumption_rate ?? 0) : 0;
                      const effectiveQty = isLaborAuto && recipeLaborHours > 0
                        ? recipeLaborHours
                        : isOvenAuto && ovenMinutes > 0
                          ? ovenAutoQty
                          : Number(cl.qty_standard);
                      const subtotal = effectiveQty * Number(rate) * (cl.headcount || 1);
                      return (
                        <TableRow key={idx}>
                          <TableCell>
                            {isEditing ? (
                              <TextField
                                select
                                SelectProps={{ native: true }}
                                value={cl.driver_id}
                                onChange={(e) => {
                                  setCostLinesDraft((prev) => {
                                    const next = [...prev];
                                    next[idx] = { ...next[idx], driver_id: e.target.value };
                                    return next;
                                  });
                                }}
                                size="small"
                                fullWidth
                              >
                                <option value="">{t('productions:recipe.selectType')}</option>
                                {costDrivers.filter((d) => d.is_active).map((d) => (
                                  <option key={d.id} value={d.id}>
                                    {d.name} ({d.unit} @ ${Number(d.default_rate).toFixed(2)})
                                  </option>
                                ))}
                              </TextField>
                            ) : (
                              <>
                                <Typography variant="body2">{driver?.name || '-'}</Typography>
                                <Typography variant="caption" color="text.secondary">{driver?.unit || ''}</Typography>
                              </>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {isLaborAuto && recipeLaborHours > 0 ? (
                              <Box>
                                <Typography variant="body2">{effectiveQty.toFixed(2)}h</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  ⚡ auto ({laborSource === 'touch' ? 'touch' : 'prep'} {laborMinutes} min)
                                </Typography>
                              </Box>
                            ) : isOvenAuto && ovenMinutes > 0 ? (
                              <Box>
                                <Typography variant="body2">{effectiveQty.toFixed(3)} {driverUnitNorm.includes('kw') ? 'kWh' : 'L'}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  🔥 auto (horno {ovenMinutes} min)
                                </Typography>
                              </Box>
                            ) : isEnergyDriver && !isOvenAuto ? (
                              <Box>
                                <Typography variant="body2" color="warning.main" sx={{ fontSize: '0.72rem' }}>⚙️ Sin consumo/hr</Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>Configura en Costos Indirectos</Typography>
                              </Box>
                            ) : isEditing ? (
                              <TextField
                                type="number"
                                value={cl.qty_standard}
                                onChange={(e) => {
                                  setCostLinesDraft((prev) => {
                                    const next = [...prev];
                                    next[idx] = { ...next[idx], qty_standard: Number(e.target.value) };
                                    return next;
                                  });
                                }}
                                size="small"
                                sx={{ width: 90 }}
                                inputProps={{ min: 0, step: 0.25 }}
                              />
                            ) : (
                              Number(cl.qty_standard).toFixed(2)
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {isEditing ? (
                              <TextField
                                type="number"
                                value={cl.headcount}
                                onChange={(e) => {
                                  setCostLinesDraft((prev) => {
                                    const next = [...prev];
                                    next[idx] = { ...next[idx], headcount: Number(e.target.value) || 1 };
                                    return next;
                                  });
                                }}
                                size="small"
                                sx={{ width: 70 }}
                                inputProps={{ min: 1 }}
                              />
                            ) : (
                              cl.headcount
                            )}
                          </TableCell>
                          <TableCell align="right">${Number(rate).toFixed(2)}</TableCell>
                          <TableCell align="right"><strong>${subtotal.toFixed(2)}</strong></TableCell>
                          {isEditing && (
                            <TableCell align="right">
                              <IconButton
                                color="error"
                                size="small"
                                onClick={() => {
                                  setCostLinesDraft((prev) => {
                                    const target = prev[idx];
                                    if (target?.id) {
                                      setDeletedCostLineIds((ids) => [...ids, target.id!]);
                                    }
                                    return prev.filter((_, i) => i !== idx);
                                  });
                                }}
                              >
                                <Delete fontSize="small" />
                              </IconButton>
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {isEditing && (
              costDrivers.length > 0 ? (
                <Button
                  size="small"
                  startIcon={<Add />}
                  onClick={() => {
                    setCostLinesDraft((prev) => [
                      ...prev,
                      { driver_id: '', qty_standard: 1, headcount: 1, rate_override: null, line_order: prev.length, _isNew: true },
                    ]);
                  }}
                  sx={{ mt: 1 }}
                >
                  {t('productions:recipe.addIndirectCost')}
                </Button>
              ) : (
                <Alert severity="warning" sx={{ borderRadius: 2.5, backgroundColor: '#fff7ed', border: '1px solid #fdba74', '& .MuiAlert-icon': { color: '#ea580c' } }}>
                  {t('productions:recipe.noCostDrivers')}
                </Alert>
              )
            )}
          </Box>
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
          <Button onClick={onClose} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>{t('productions:recipe.close')}</Button>
        </Box>
      </DialogActions>

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
