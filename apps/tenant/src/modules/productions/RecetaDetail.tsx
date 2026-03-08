/**
 * RecetaDetail - Vista detallada de receta con desglose de costos
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Typography, Box, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Divider, Alert, CircularProgress, Grid,
  TextField, IconButton
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

const VALID_UNITS = new Set(['kg', 'g', 'lb', 'oz', 'ton', 'mg', 'L', 'ml', 'gal', 'qt', 'pt', 'cup', 'fl_oz', 'tbsp', 'tsp', 'uds', 'unidades', 'pcs']);

const normalizeRecipeUnit = (unit?: string | null): string => {
  const u = String(unit || '').trim().toLowerCase();
  if (!u || u === '-' || /^\d+$/.test(u)) return 'uds';
  if (u === 'unit' || u === 'units' || u === 'und' || u === 'uni') return 'uds';
  if (u === 'unidad' || u === 'unid' || u === 'pza' || u === 'pieza' || u === 'cantidad') return 'unidades';
  if (u === 'gr' || u === 'gramo' || u === 'gramos') return 'g';
  if (u === 'kilo' || u === 'kilos' || u === 'kilogramo' || u === 'kilogramos') return 'kg';
  if (u === 'lbs' || u === 'pounds' || u === 'libra' || u === 'libras') return 'lb';
  if (u === 'lt' || u === 'litr' || u === 'litro' || u === 'litros') return 'L';
  for (const valid of VALID_UNITS) {
    if (u === valid.toLowerCase()) return valid;
  }
  return 'uds';
};

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

  const [loading, setLoading] = useState(true);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [orderPromptOpen, setOrderPromptOpen] = useState(false);
  const [customOrderQty, setCustomOrderQty] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
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
            unit: normalizeRecipeUnit(ing.unit),
            purchase_packaging: String(ing.purchase_packaging || ''),
            qty_per_package: Math.max(Number(ing.qty_per_package || 1), 0.0001),
            package_unit: normalizeRecipeUnit(ing.package_unit),
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
        overhead_pct: (recipeData as any).overhead_pct ?? 5,
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
    if (!recipe || !breakdown) return;

    try {
      setUpdating(true);
      const unitCost = Number(breakdown.costo_por_unidad ?? 0);
      const newPrice = unitCost * multiplier;

      await tenantApi.put(`/api/v1/tenant/products/${recipe.product_id}`, {
        price: Number(newPrice.toFixed(2)),
        cost_price: Number(unitCost.toFixed(4))
      });

      alert(`${t('productions:recipe.priceUpdated')} $${newPrice.toFixed(2)} (${t('productions:recipe.margin')} ${((multiplier - 1) * 100).toFixed(0)}%)`);
    } catch (err: any) {
      alert(`${t('productions:recipe.errorUpdatingPrice')}: ` + (err.message || 'Unknown error'));
    } finally {
      setUpdating(false);
    }
  };

  const setIngredientField = (index: number, field: string, value: any) => {
    setIngredientsDraft((prev) => {
      const next = [...prev];
      (next[index] as any)[field] = value;
      if (field === 'product_id') {
        const p = products.find((x) => x.id === value);
        if (p) {
          next[index].unit = normalizeRecipeUnit(p.unit);
          next[index].package_unit = normalizeRecipeUnit(p.unit);
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
    if (!recipe) return;
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
          unit: normalizeRecipeUnit(row.unit),
          purchase_packaging: String(row.purchase_packaging || '-'),
          qty_per_package: Math.max(Number(row.qty_per_package || 1), 0.0001),
          package_unit: normalizeRecipeUnit(row.package_unit || row.unit),
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
    const baseQty = Number(recipe?.yield_qty || 1);
    setCustomOrderQty(String(baseQty > 0 ? baseQty : 1));
    setOrderPromptOpen(true);
  };

  const submitOrderWithQty = (qty: number) => {
    if (!recipe || !onCreateOrder) return;
    const safeQty = Number.isFinite(qty) && qty > 0 ? qty : Number(recipe.yield_qty || 1);
    onCreateOrder(recipe, { qty: safeQty, autoCreate: true });
    setOrderPromptOpen(false);
  };

  const startInlineEdit = () => {
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

  const totalCost = Number(breakdown.costo_total ?? 0);
  const unitCost = Number(breakdown.costo_por_unidad ?? 0);
  const ingredientsCount = Number(breakdown.ingredientes_count ?? 0);
  const breakdownRows = Array.isArray(breakdown.desglose) ? breakdown.desglose : [];

  const fc = fullCost;
  const hasIndirect = fc && (
    Number(fc.indirect_total || 0) > 0 ||
    Number(fc.waste_cost || 0) > 0 ||
    Number(fc.overhead_cost || 0) > 0
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth PaperProps={{ sx: dialogPaperSx }}>
      <DialogTitle
        component="div"
        sx={{
          px: { xs: 2, md: 3 },
          py: { xs: 2, md: 2.5 },
          borderBottom: '1px solid #e5e7eb',
          backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        }}
      >
        <Typography variant="h5" component="h2" sx={{ fontWeight: 700 }}>
          {recipe.name}
        </Typography>
        <Typography variant="body2" component="p" color="text.secondary" sx={{ mt: 0.5 }}>
          {recipe.product_name}
        </Typography>
      </DialogTitle>

      <DialogContent
        dividers
        sx={{
          px: { xs: 2, md: 3 },
          py: { xs: 2, md: 3 },
          borderColor: '#e5e7eb',
          backgroundColor: '#f8fafc',
        }}
      >
        {!isEditing && (
          <Alert severity="info" sx={{ ...infoAlertSx, mb: 3, fontWeight: 600 }}>
            Haz clic en parametros, ingredientes o costos para editar.
          </Alert>
        )}

        {/* Resumen */}
        <Box
          sx={{ ...sectionCardSx, ...(isEditing ? {} : clickableSectionSx) }}
          onClick={isEditing ? undefined : startInlineEdit}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 1.5, flexWrap: 'wrap' }}>
            <Typography variant="overline" sx={{ color: '#64748b', letterSpacing: 1.2 }}>
              Resumen de receta
            </Typography>
            {!isEditing && (
              <Typography variant="caption" sx={{ color: '#2563eb', fontWeight: 600 }}>
                Haz clic para editar rendimiento
              </Typography>
            )}
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Box sx={metricCardSx}>
                <Typography variant="caption" color="text.secondary">
                  {t('productions:recipe.yield')}
                </Typography>
                {isEditing ? (
                  <TextField
                    type="number"
                    size="small"
                    fullWidth
                    value={yieldQtyDraft ?? ''}
                    onChange={(e) => setYieldQtyDraft(e.target.value ? Number(e.target.value) : null)}
                    inputProps={{ min: 1, step: 1 }}
                    helperText="Unidades producidas por receta"
                    sx={{ mt: 1 }}
                  />
                ) : (
                  <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>{recipe.yield_qty} uds</Typography>
                )}
              </Box>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Box sx={metricCardSx}>
                <Typography variant="caption" color="text.secondary">
                  {t('productions:recipe.materialsCost')}
                </Typography>
                <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>${totalCost.toFixed(2)}</Typography>
                <Typography variant="caption" color="text.secondary">
                  /u: ${unitCost.toFixed(4)}
                </Typography>
              </Box>
            </Grid>

            {hasIndirect ? (
              <>
                <Grid item xs={6} sm={3}>
                  <Box sx={metricCardSx}>
                    <Typography variant="caption" color="text.secondary">
                      Costo total (lote)
                    </Typography>
                    <Typography variant="h6" color="error.main" sx={{ mt: 0.5, fontWeight: 700 }}>
                      ${Number(fc.full_cost_total).toFixed(2)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      materiales + merma + deprec. + M.O.
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={metricCardSx}>
                    <Typography variant="caption" color="text.secondary">
                      {t('productions:recipe.fullCostUnit')}
                    </Typography>
                    <Typography variant="h6" color="error.main" sx={{ mt: 0.5, fontWeight: 700 }}>
                      ${Number(fc.full_cost_unit).toFixed(4)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      por unidad producida
                    </Typography>
                  </Box>
                </Grid>
                {/* Desglose detallado de costos */}
                <Grid item xs={12}>
                  <Box sx={{ border: '1px solid #e2e8f0', borderRadius: 2, overflow: 'hidden', mt: 0.5 }}>
                    <Box sx={{ px: 2, py: 1, background: '#f1f5f9', borderBottom: '1px solid #e2e8f0' }}>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: '#475569', letterSpacing: 0.8 }}>
                        DESGLOSE DE COSTO — {recipe.yield_qty} unidades
                      </Typography>
                    </Box>
                    {/* Materiales */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9' }}>
                      <Typography variant="body2" color="text.secondary">Costo de materiales</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>${Number(fc.materials_total).toFixed(2)}</Typography>
                    </Box>
                    {/* Merma */}
                    {Number(fc.waste_cost || 0) > 0 && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9', background: '#fff7ed' }}>
                        <Typography variant="body2" color="warning.dark">
                          Merma ({fc.waste_pct}%)
                        </Typography>
                        <Typography variant="body2" color="warning.dark" sx={{ fontWeight: 600 }}>
                          ${Number(fc.waste_cost).toFixed(2)}
                        </Typography>
                      </Box>
                    )}
                    {/* Depreciación */}
                    {Number(fc.overhead_cost || 0) > 0 && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9', background: '#f0fdf4' }}>
                        <Typography variant="body2" color="success.dark">
                          Depreciación de equipos ({fc.overhead_pct}%)
                        </Typography>
                        <Typography variant="body2" color="success.dark" sx={{ fontWeight: 600 }}>
                          ${Number(fc.overhead_cost).toFixed(2)}
                        </Typography>
                      </Box>
                    )}
                    {/* Mano de obra */}
                    {Number(fc.labor_with_burden_factor || fc.labor_total || 0) > 0 && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9' }}>
                        <Typography variant="body2" color="text.secondary">Mano de obra</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          ${Number(fc.labor_with_burden_factor || fc.labor_total).toFixed(2)}
                        </Typography>
                      </Box>
                    )}
                    {/* Energía / Diesel */}
                    {(Number(fc.electricity_total || 0) + Number(fc.diesel_total || 0)) > 0 && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9' }}>
                        <Typography variant="body2" color="text.secondary">
                          Energía / Combustible
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          ${(Number(fc.electricity_total || 0) + Number(fc.diesel_total || 0)).toFixed(2)}
                        </Typography>
                      </Box>
                    )}
                    {/* Otros indirectos */}
                    {Number(fc.other_indirect_total || 0) > 0 && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, borderBottom: '1px solid #f1f5f9' }}>
                        <Typography variant="body2" color="text.secondary">Otros costos indirectos</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          ${Number(fc.other_indirect_total).toFixed(2)}
                        </Typography>
                      </Box>
                    )}
                    {/* Total */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 1, background: '#1e293b' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#f8fafc' }}>
                        COSTO TOTAL ({recipe.yield_qty} uds)
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#fbbf24' }}>
                        ${Number(fc.full_cost_total).toFixed(2)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 2, py: 0.75, background: '#0f172a' }}>
                      <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                        Costo por unidad
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: '#34d399' }}>
                        ${Number(fc.full_cost_unit).toFixed(4)} / u
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              </>
            ) : (
              <>
                <Grid item xs={6} sm={3}>
                  <Box sx={metricCardSx}>
                    <Typography variant="caption" color="text.secondary">
                      {t('productions:recipe.costUnit')}
                    </Typography>
                    <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>${unitCost.toFixed(4)}</Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={metricCardSx}>
                    <Typography variant="caption" color="text.secondary">
                      {t('productions:recipe.ingredients')}
                    </Typography>
                    <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>{ingredientsCount}</Typography>
                  </Box>
                </Grid>
              </>
            )}
          </Grid>
        </Box>

        {/* Parámetros de producción */}
        {isEditing ? (
          <Box sx={{ ...sectionCardSx, ...fieldGroupSx }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 2 }}>
              <Typography variant="subtitle2">
              {t('productions:recipe.productionParameters')}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748b' }}>
                Edicion rapida
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
              {/* TOUCH vs PROCESO */}
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
                  helperText="Pérdida de materiales en proceso"
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <TextField
                  label="% Depreciación equipos"
                  type="number"
                  size="small"
                  fullWidth
                  value={prodParams.overhead_pct ?? 5}
                  onChange={(e) => setProdParams((p) => ({ ...p, overhead_pct: e.target.value ? Number(e.target.value) : null }))}
                  inputProps={{ min: 0, max: 100, step: 0.1 }}
                  helperText="Amortización de maquinaria (default 5%)"
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
              <Grid item xs={12} sm={6}>
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
          <Box
            sx={{ ...sectionCardSx, ...clickableSectionSx, display: 'flex', flexWrap: 'wrap', gap: 1, '& .MuiChip-root': { borderRadius: 2 } }}
            onClick={startInlineEdit}
          >
            <Box sx={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t('productions:recipe.productionParameters')}
              </Typography>
              <Typography variant="caption" sx={{ color: '#2563eb', fontWeight: 600 }}>
                Haz clic para editar
              </Typography>
            </Box>
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
            {(recipe as any).overhead_pct != null && (recipe as any).overhead_pct > 0 && (
              <Chip label={`🔧 Depreciación: ${(recipe as any).overhead_pct}%`} color="warning" size="small" />
            )}
            {recipe.trays_per_batch != null && (
              <Chip label={`🍞 ${recipe.trays_per_batch} ${t('productions:recipe.traysLabel')}`} color="default" size="small" />
            )}
            {recipe.units_per_tray != null && (
              <Chip label={`${recipe.units_per_tray} ${t('productions:recipe.unitsPerTrayLabel')}`} color="default" size="small" />
            )}
          </Box>
        )}

        <Divider sx={{ my: 3, borderColor: '#e2e8f0' }} />

        {/* Desglose de ingredientes */}
        <Box
          sx={{ ...sectionCardSx, ...(isEditing ? {} : clickableSectionSx), mb: 3 }}
          onClick={isEditing ? undefined : startInlineEdit}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 1.5, flexWrap: 'wrap' }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {t('productions:recipe.ingredientsBreakdown')}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748b' }}>
                {isEditing ? 'Edita ingredientes directamente en la tabla.' : 'Haz clic en la tabla para editar ingredientes.'}
              </Typography>
            </Box>
            {isEditing && (
              <Button
                size="small"
                startIcon={<Add />}
                onClick={(event) => {
                  event.stopPropagation();
                  addNewIngredientRow();
                }}
                sx={{ borderRadius: 2.5, fontWeight: 600 }}
              >
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
                    <TableCell colSpan={3} align="center">Compra</TableCell>
                    <TableCell rowSpan={2} align="right">% {t('productions:recipe.cost')}</TableCell>
                    <TableCell rowSpan={2} align="right">{t('productions:recipe.actionsColumn')}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell align="right">{t('productions:recipe.quantity')}</TableCell>
                    <TableCell>Unidad</TableCell>
                    <TableCell>{t('productions:recipe.packaging')}</TableCell>
                    <TableCell align="right">Contenido</TableCell>
                    <TableCell align="right">Costo pack</TableCell>
                  </TableRow>
                </>
              ) : (
                <TableRow>
                  <TableCell>{t('productions:recipe.ingredients')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.quantity')}</TableCell>
                  <TableCell align="right">Kg / Lb</TableCell>
                  <TableCell>{t('productions:recipe.packaging')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.cost')}</TableCell>
                  <TableCell align="right">% {t('productions:recipe.cost')}</TableCell>
                </TableRow>
              )}
            </TableHead>
            <TableBody>
              {ingredientsDraft.length === 0 && (
                <TableRow>
                  <TableCell colSpan={isEditing ? 9 : 6} align="center">
                    <Typography variant="body2" color="text.secondary">
                      {t('productions:recipe.noIngredients')}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {ingredientsDraft.map((item, index) => {
                const product = products.find((p) => p.id === item.product_id);
                const productName = product?.name || (item as any)?.product_name || '-';
                const qty = Number(item.qty ?? 0);
                const unitNorm = normalizeRecipeUnit(item.unit);
                let kgLbText: string | null = null;
                if (unitNorm === 'g') {
                  const kg = qty / 1000;
                  const lb = qty / 453.592;
                  kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                } else if (unitNorm === 'kg') {
                  const kg = qty;
                  const lb = qty * 2.20462;
                  kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                } else if (unitNorm === 'lb') {
                  const lb = qty;
                  const kg = qty / 2.20462;
                  kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                } else if (unitNorm === 'oz') {
                  const lb = qty / 16;
                  const kg = lb / 2.20462;
                  kgLbText = `${kg.toFixed(3)} kg / ${lb.toFixed(3)} lb`;
                }
                const estimatedCost =
                  Number(item.package_cost || 0) * (Number(item.qty || 0) / Math.max(Number(item.qty_per_package || 1), 1));
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
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
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
                        value={item.unit}
                        onChange={(e) => setIngredientField(index, 'unit', e.target.value)}
                        size="small"
                        sx={{ width: 90 }}
                      />
                    </TableCell>
                  )}
                  <TableCell align="right">
                    {kgLbText ? (
                      <Typography variant="body2" color="text.secondary">
                        {kgLbText}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {isEditing ? (
                      <TextField
                        value={item.purchase_packaging || ''}
                        onChange={(e) => setIngredientField(index, 'purchase_packaging', e.target.value)}
                        size="small"
                        fullWidth
                      />
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {item.purchase_packaging || '-'}
                      </Typography>
                    )}
                  </TableCell>
                  {isEditing ? (
                    <>
                      <TableCell align="right">
                        <TextField
                          type="number"
                          value={item.qty_per_package}
                          onChange={(e) => setIngredientField(index, 'qty_per_package', Number(e.target.value))}
                          size="small"
                          sx={{ width: 90 }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <TextField
                          type="number"
                          value={item.package_cost}
                          onChange={(e) => setIngredientField(index, 'package_cost', Number(e.target.value))}
                          size="small"
                          sx={{ width: 100 }}
                        />
                      </TableCell>
                    </>
                  ) : (
                    <TableCell align="right">
                      <strong>${estimatedCost.toFixed(2)}</strong>
                    </TableCell>
                  )}
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
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
        </Box>

        {/* Costos indirectos */}
        <Divider sx={{ my: 3, borderColor: '#e2e8f0' }} />
        <Box
          sx={{ ...sectionCardSx, ...(isEditing ? {} : clickableSectionSx), mb: 3 }}
          onClick={isEditing ? undefined : startInlineEdit}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 1.5, flexWrap: 'wrap' }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {t('productions:recipe.indirectCosts')}
              </Typography>
              <Typography variant="caption" sx={{ color: '#64748b' }}>
                {isEditing ? 'Ajusta mano de obra y costos por driver.' : 'Haz clic para editar costos indirectos.'}
              </Typography>
            </Box>
          </Box>

        {costDrivers.length === 0 && !isEditing && (
          <Alert severity="info" sx={{ ...infoAlertSx, mb: 0 }}>
            {t('productions:recipe.noCostDriversInfo')}
          </Alert>
        )}

        {(costLinesDraft.length > 0 || isEditing) && (
          <TableContainer component={Paper} variant="outlined" sx={{ ...tableContainerSx, mb: 0 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('productions:recipe.costType')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.qty')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.headcount')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.rate')}</TableCell>
                  <TableCell align="right">{t('productions:recipe.subtotal')}</TableCell>
                  {isEditing && <TableCell align="right">{t('productions:recipe.actionsColumn')}</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {costLinesDraft.map((cl, idx) => {
                  const driver = costDrivers.find((d) => d.id === cl.driver_id);
                  const rate = cl.rate_override ?? (driver?.default_rate || 0);
                  const driverUnitNorm = normalizeCostDriverUnit(driver?.unit);
                  const isLaborAuto = isLaborAutoDriver(driver);
                  // Cualquier driver con consumption_rate > 0 que no sea labor → auto-calcula desde tiempo de horno
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
                            <Typography variant="body2" color="warning.main" sx={{ fontSize: '0.72rem' }}>
                              ⚙️ Sin consumo/hr
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                              Configura en Costos Indirectos
                            </Typography>
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
                      <TableCell align="right">
                        ${Number(rate).toFixed(2)}
                      </TableCell>
                      <TableCell align="right">
                        <strong>${subtotal.toFixed(2)}</strong>
                      </TableCell>
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
                  {
                    driver_id: '',
                    qty_standard: 1,
                    headcount: 1,
                    rate_override: null,
                    line_order: prev.length,
                    _isNew: true,
                  },
                ]);
              }}
              sx={{ mb: 2 }}
            >
              {t('productions:recipe.addIndirectCost')}
            </Button>
          ) : (
            <Alert severity="warning" sx={{ mb: 2, borderRadius: 2.5, backgroundColor: '#fff7ed', border: '1px solid #fdba74', '& .MuiAlert-icon': { color: '#ea580c' } }}>
              {t('productions:recipe.noCostDrivers')}
            </Alert>
          )
        )}
        </Box>

        {/* Instrucciones (solo lectura) */}
        {!isEditing && recipe.instructions && (
          <>
            <Divider sx={{ my: 3, borderColor: '#e2e8f0' }} />
            <Box
              sx={{ ...sectionCardSx, ...clickableSectionSx, mb: 0 }}
              onClick={startInlineEdit}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {t('productions:recipe.instructions')}
                </Typography>
                <Typography variant="caption" sx={{ color: '#2563eb', fontWeight: 600 }}>
                  Haz clic para editar
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.7 }}>
                {recipe.instructions}
              </Typography>
            </Box>
          </>
        )}
      </DialogContent>

      <DialogActions sx={dialogActionsSx}>
        {isEditing ? (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button
              variant="text"
              onClick={handleCancelEditing}
              disabled={updating}
              sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}
            >
              Cancelar edicion
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleSaveIngredients}
              disabled={updating}
              sx={{ minWidth: 160, borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
            >
              Guardar cambios
            </Button>
          </Box>
        ) : (
          <Box />
        )}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', marginLeft: 'auto' }}>
          {onCreateOrder && recipe && (
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

      <Dialog open={orderPromptOpen} onClose={() => setOrderPromptOpen(false)} maxWidth="xs" fullWidth PaperProps={{ sx: dialogPaperSx }}>
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
              $
              {(
                Number(breakdown?.costo_por_unidad || 0) *
                Math.max(Number(customOrderQty || 0), 0)
              ).toFixed(2)}
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
