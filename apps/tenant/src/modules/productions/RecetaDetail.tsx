/**
 * RecetaDetail - Vista detallada de receta con desglose de costos
 */

import React, { useState, useEffect } from 'react';
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
  addIngredient,
  updateIngredient,
  deleteIngredient,
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
import { useI18n } from '../../i18n/I18nProvider';
import tenantApi from '../../shared/api/client';

interface RecetaDetailProps {
  open: boolean;
  recipeId: string;
  onClose: () => void;
  onCreateOrder?: (recipe: Recipe, options?: { qty?: number; autoCreate?: boolean }) => void;
  onEdit?: (recipe: Recipe) => void;
}

export default function RecetaDetail({ open, recipeId, onClose, onCreateOrder, onEdit }: RecetaDetailProps) {
  const { lang } = useI18n();
  const isEs = String(lang || 'en').toLowerCase().startsWith('es');
  const L = (en: string, es: string) => (isEs ? es : en);

  const [loading, setLoading] = useState(true);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [orderPromptOpen, setOrderPromptOpen] = useState(false);
  const [customOrderQty, setCustomOrderQty] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [deletedIngredientIds, setDeletedIngredientIds] = useState<string[]>([]);
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
    waste_pct: null as number | null,
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
      const recipeIngredients = Array.isArray(recipeData.ingredients) ? recipeData.ingredients : [];
      setIngredientsDraft(
        recipeIngredients.map((ing: RecipeIngredientResponse, idx: number) => ({
          id: ing.id,
          product_id: String(ing.product_id || ''),
          qty: Number(ing.qty || 0),
          unit: String(ing.unit || 'uds'),
          purchase_packaging: String(ing.purchase_packaging || ''),
          qty_per_package: Number(ing.qty_per_package || 1),
          package_unit: String(ing.package_unit || 'uds'),
          package_cost: Number(ing.package_cost || 0),
          notes: ing.notes || '',
          line_order: typeof ing.line_order === 'number' ? ing.line_order : idx,
        }))
      );
      setDeletedIngredientIds([]);
      setProdParams({
        prep_time_minutes: recipeData.prep_time_minutes ?? null,
        baking_time_minutes: recipeData.baking_time_minutes ?? null,
        oven_temp_celsius: recipeData.oven_temp_celsius ?? null,
        rest_time_minutes: recipeData.rest_time_minutes ?? null,
        waste_pct: recipeData.waste_pct ?? null,
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
      setError(err.message || L('Error loading data', 'Error al cargar datos'));
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

      alert(`${L('Price updated to', 'Precio actualizado a')} $${newPrice.toFixed(2)} (${L('margin', 'margen')} ${((multiplier - 1) * 100).toFixed(0)}%)`);
    } catch (err: any) {
      alert(`${L('Error updating price', 'Error al actualizar precio')}: ` + (err.message || 'Unknown error'));
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
          next[index].unit = String(p.unit || 'uds');
          next[index].package_unit = String(p.unit || 'uds');
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
    setIngredientsDraft((prev) => {
      const target = prev[index];
      if (target?.id) {
        setDeletedIngredientIds((ids) => [...ids, target.id!]);
      }
      return prev.filter((_, i) => i !== index);
    });
  };

  const handleSaveIngredients = async () => {
    if (!recipe) return;
    try {
      setUpdating(true);
      setError(null);

      await updateRecipe(recipe.id, {
        prep_time_minutes: prodParams.prep_time_minutes ?? undefined,
        baking_time_minutes: prodParams.baking_time_minutes ?? undefined,
        oven_temp_celsius: prodParams.oven_temp_celsius ?? undefined,
        rest_time_minutes: prodParams.rest_time_minutes ?? undefined,
        waste_pct: prodParams.waste_pct ?? undefined,
        trays_per_batch: (prodParams.trays_per_batch && prodParams.trays_per_batch >= 1) ? prodParams.trays_per_batch : undefined,
        units_per_tray: (prodParams.units_per_tray && prodParams.units_per_tray >= 1) ? prodParams.units_per_tray : undefined,
        instructions: prodParams.instructions || undefined,
      });

      for (const ingredientId of deletedIngredientIds) {
        await deleteIngredient(recipe.id, ingredientId);
      }

      for (const row of ingredientsDraft) {
        if (!row.product_id || Number(row.qty || 0) <= 0) continue;
        const payload = {
          product_id: row.product_id,
          qty: Number(row.qty || 0),
          unit: String(row.unit || 'uds'),
          purchase_packaging: String(row.purchase_packaging || '-'),
          qty_per_package: Number(row.qty_per_package || 1),
          package_unit: String(row.package_unit || row.unit || 'uds'),
          package_cost: Number(row.package_cost || 0),
          notes: row.notes || undefined,
          line_order: Number(row.line_order || 0),
        };
        if (row._isNew || !row.id) {
          await addIngredient(recipe.id, payload as any);
        } else {
          await updateIngredient(recipe.id, row.id, payload as any);
        }
      }

      // Save cost lines
      for (const clId of deletedCostLineIds) {
        await deleteRecipeCostLine(recipe.id, clId);
      }
      for (const cl of costLinesDraft) {
        if (!cl.driver_id) continue;
        const clPayload = {
          driver_id: cl.driver_id,
          qty_standard: Number(cl.qty_standard || 0),
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
        : err?.message || L('Error saving ingredients', 'Error guardando ingredientes');
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
          <Alert severity="error">{error || 'No se pudo cargar la receta'}</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    );
  }

  const totalCost = Number(breakdown.costo_total ?? 0);
  const unitCost = Number(breakdown.costo_por_unidad ?? 0);
  const ingredientsCount = Number(breakdown.ingredientes_count ?? 0);
  const breakdownRows = Array.isArray(breakdown.desglose) ? breakdown.desglose : [];

  const fc = fullCost;
  const hasIndirect = fc && Number(fc.indirect_total || 0) > 0;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Typography variant="h5">{recipe.name}</Typography>
        <Typography variant="body2" color="text.secondary">
          {recipe.product_name}
        </Typography>
      </DialogTitle>

      <DialogContent dividers>
        {/* Resumen */}
        <Box mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                {L('Yield', 'Rendimiento')}
              </Typography>
              <Typography variant="h6">{recipe.yield_qty} uds</Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                {L('Materials Cost', 'Costo Materiales')}
              </Typography>
              <Typography variant="h6">${totalCost.toFixed(2)}</Typography>
              <Typography variant="caption" color="text.secondary">
                /u: ${unitCost.toFixed(4)}
              </Typography>
            </Grid>

            {hasIndirect ? (
              <>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    {L('Indirect Costs', 'Costos Indirectos')}
                  </Typography>
                  <Typography variant="h6" color="warning.main">
                    ${Number(fc.indirect_total).toFixed(2)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {Number(fc.labor_total) > 0 && `MO: $${Number(fc.labor_total).toFixed(2)} `}
                    {Number(fc.energy_total) > 0 && `Energía: $${Number(fc.energy_total).toFixed(2)}`}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    {L('Full Cost/Unit', 'Costo Completo/U')}
                  </Typography>
                  <Typography variant="h6" color="error.main">
                    ${Number(fc.full_cost_unit).toFixed(4)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total: ${Number(fc.full_cost_total).toFixed(2)}
                  </Typography>
                </Grid>
              </>
            ) : (
              <>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    {L('Cost/Unit', 'Costo/Unidad')}
                  </Typography>
                  <Typography variant="h6">${unitCost.toFixed(4)}</Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    {L('Ingredients', 'Ingredientes')}
                  </Typography>
                  <Typography variant="h6">{ingredientsCount}</Typography>
                </Grid>
              </>
            )}
          </Grid>
        </Box>

        {/* Parámetros de producción */}
        {isEditing ? (
          <Box mb={2}>
            <Typography variant="subtitle2" gutterBottom>
              {L('Production Parameters', 'Parámetros de Producción')}
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6} sm={3}>
                <TextField
                  label={L('Prep time (min)', 'T. preparación (min)')}
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
                  label={L('Baking time (min)', 'T. horneado (min)')}
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
                  label={L('Oven temp (°C)', 'Temp. horno (°C)')}
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
                  label={L('Rest time (min)', 'T. reposo (min)')}
                  type="number"
                  size="small"
                  fullWidth
                  value={prodParams.rest_time_minutes ?? ''}
                  onChange={(e) => setProdParams((p) => ({ ...p, rest_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                  inputProps={{ min: 0 }}
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <TextField
                  label={L('Waste %', 'Merma %')}
                  type="number"
                  size="small"
                  fullWidth
                  value={prodParams.waste_pct ?? ''}
                  onChange={(e) => setProdParams((p) => ({ ...p, waste_pct: e.target.value ? Number(e.target.value) : null }))}
                  inputProps={{ min: 0, max: 100, step: 0.1 }}
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <TextField
                  label={L('Trays/batch', 'Bandejas/lote')}
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
                  label={L('Units/tray', 'Uds/bandeja')}
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
                  label={L('Instructions', 'Instrucciones')}
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
          <Box mb={2} display="flex" flexWrap="wrap" gap={1}>
            {recipe.prep_time_minutes != null && (
              <Chip label={`⏱️ ${L('Prep', 'Prep.')}: ${recipe.prep_time_minutes} min`} color="primary" size="small" />
            )}
            {recipe.baking_time_minutes != null && (
              <Chip label={`🔥 ${L('Baking', 'Horneado')}: ${recipe.baking_time_minutes} min`} color="warning" size="small" />
            )}
            {recipe.oven_temp_celsius != null && (
              <Chip label={`🌡️ ${recipe.oven_temp_celsius} °C`} color="default" size="small" />
            )}
            {recipe.rest_time_minutes != null && (
              <Chip label={`⏸️ ${L('Rest', 'Reposo')}: ${recipe.rest_time_minutes} min`} color="info" size="small" />
            )}
            {recipe.waste_pct != null && recipe.waste_pct > 0 && (
              <Chip label={`📉 ${L('Waste', 'Merma')}: ${recipe.waste_pct}%`} color="error" size="small" />
            )}
            {recipe.trays_per_batch != null && (
              <Chip label={`🍞 ${recipe.trays_per_batch} ${L('trays', 'bandejas')}`} color="default" size="small" />
            )}
            {recipe.units_per_tray != null && (
              <Chip label={`${recipe.units_per_tray} ${L('units/tray', 'uds/bandeja')}`} color="default" size="small" />
            )}
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Desglose de ingredientes */}
        <Typography variant="h6" gutterBottom>
          {L('Ingredients Breakdown', 'Desglose de Ingredientes')}
        </Typography>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ingrediente</TableCell>
                <TableCell align="right">{L('Quantity', 'Cantidad')}</TableCell>
                <TableCell align="right">Kg / Lb</TableCell>
                <TableCell>{L('Packaging', 'Presentación')}</TableCell>
                <TableCell align="right">{L('Cost', 'Costo')}</TableCell>
                <TableCell align="right">% {L('Cost', 'Costo')}</TableCell>
                {isEditing && <TableCell align="right">{L('Actions', 'Acciones')}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {ingredientsDraft.length === 0 && (
                <TableRow>
                  <TableCell colSpan={isEditing ? 7 : 6} align="center">
                    <Typography variant="body2" color="text.secondary">
                      {L('This recipe has no ingredients yet.', 'Esta receta no tiene ingredientes registrados.')}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {ingredientsDraft.map((item, index) => {
                const product = products.find((p) => p.id === item.product_id);
                const productName = product?.name || (item as any)?.product_name || '-';
                const qty = Number(item.qty ?? 0);
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
                        <option value="">{L('Select product', 'Seleccionar producto')}</option>
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
                      <Box display="flex" alignItems="center" justifyContent="flex-end" gap={1}>
                        <TextField
                          type="number"
                          value={item.qty}
                          onChange={(e) => setIngredientField(index, 'qty', Number(e.target.value))}
                          size="small"
                          sx={{ width: 90 }}
                        />
                        <TextField
                          value={item.unit}
                          onChange={(e) => setIngredientField(index, 'unit', e.target.value)}
                          size="small"
                          sx={{ width: 90 }}
                        />
                      </Box>
                    ) : (
                      `${qty.toFixed(2)} ${item.unit || ''}`
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {item.unit === 'g' ? (
                      <Typography variant="body2" color="text.secondary">
                        {(qty / 1000).toFixed(3)} kg / {(qty / 453.592).toFixed(3)} lb
                      </Typography>
                    ) : item.unit === 'kg' ? (
                      <Typography variant="body2" color="text.secondary">
                        {qty.toFixed(3)} kg / {(qty * 2.20462).toFixed(3)} lb
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
                  <TableCell align="right">
                    {isEditing ? (
                      <Box display="flex" alignItems="center" justifyContent="flex-end" gap={1}>
                        <TextField
                          type="number"
                          value={item.package_cost}
                          onChange={(e) => setIngredientField(index, 'package_cost', Number(e.target.value))}
                          size="small"
                          sx={{ width: 90 }}
                        />
                        <TextField
                          type="number"
                          value={item.qty_per_package}
                          onChange={(e) => setIngredientField(index, 'qty_per_package', Number(e.target.value))}
                          size="small"
                          sx={{ width: 90 }}
                        />
                      </Box>
                    ) : (
                      <strong>${estimatedCost.toFixed(2)}</strong>
                    )}
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
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Costos indirectos */}
        <Divider sx={{ my: 2 }} />
        <Typography variant="h6" gutterBottom>
          {L('Indirect Costs', 'Costos Indirectos')}
        </Typography>

        {costDrivers.length === 0 && !isEditing && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {L(
              'No cost drivers configured. Go to production settings to add labor, energy, and other cost types.',
              'No hay drivers de costo configurados. Agrega tipos como Mano de Obra, Energía, etc. desde los ajustes de producción.'
            )}
          </Alert>
        )}

        {(costLinesDraft.length > 0 || isEditing) && (
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{L('Cost Type', 'Tipo de Costo')}</TableCell>
                  <TableCell align="right">{L('Qty', 'Cantidad')}</TableCell>
                  <TableCell align="right">{L('Headcount', 'Personas')}</TableCell>
                  <TableCell align="right">{L('Rate', 'Tarifa')}</TableCell>
                  <TableCell align="right">{L('Subtotal', 'Subtotal')}</TableCell>
                  {isEditing && <TableCell align="right">{L('Actions', 'Acciones')}</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {costLinesDraft.map((cl, idx) => {
                  const driver = costDrivers.find((d) => d.id === cl.driver_id);
                  const rate = cl.rate_override ?? (driver?.default_rate || 0);
                  const driverCode = (driver?.code || '').toUpperCase();
                  const isLaborAuto = driver && (
                    driverCode.startsWith('LABOR')
                    || ((driver.unit || '').toLowerCase() === 'hour'
                        && !driverCode.startsWith('ENERGY')
                        && !driverCode.startsWith('OVEN'))
                  );
                  const recipeLaborHours = (prodParams.prep_time_minutes || 0) / 60;
                  const effectiveQty = isLaborAuto && recipeLaborHours > 0 ? recipeLaborHours : Number(cl.qty_standard);
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
                            <option value="">{L('Select type', 'Seleccionar tipo')}</option>
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
                            <Typography variant="caption" color="text.secondary">⚡ auto (prep)</Typography>
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
              {L('Add indirect cost', 'Añadir costo indirecto')}
            </Button>
          ) : (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {L(
                'No cost types configured yet. Go to Production → Indirect Costs to create them first.',
                'No hay tipos de costo configurados. Ve a Producción → Costos indirectos para crearlos primero.'
              )}
            </Alert>
          )
        )}

        {/* Instrucciones (solo lectura) */}
        {!isEditing && recipe.instructions && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              {L('Instructions', 'Instrucciones')}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {recipe.instructions}
            </Typography>
          </>
        )}
      </DialogContent>

      <DialogActions>
        {isEditing ? (
          <Button
            variant="contained"
            color="primary"
            onClick={handleSaveIngredients}
            disabled={updating}
          >
            {L('Save', 'Guardar')}
          </Button>
        ) : (
          <Button
            variant="outlined"
            onClick={() => setIsEditing(true)}
            disabled={updating}
          >
            {L('Edit', 'Editar')}
          </Button>
        )}
        <Button
          variant="outlined"
          startIcon={<Add />}
          onClick={addNewIngredientRow}
          disabled={updating}
        >
          {L('Add new ingredient', 'Añadir nuevo ingrediente')}
        </Button>
        {onEdit && recipe && !isEditing && (
          <Button
            variant="text"
            onClick={() => onEdit(recipe)}
            disabled={updating}
          >
            {L('Open full editor', 'Abrir editor completo')}
          </Button>
        )}
        {onCreateOrder && recipe && (
          <Button
            variant="contained"
            color="primary"
            onClick={openOrderPrompt}
            disabled={updating}
          >
            {L('New Order', 'Nueva Orden')}
          </Button>
        )}
        <Button onClick={onClose}>{L('Close', 'Cerrar')}</Button>
      </DialogActions>

      <Dialog open={orderPromptOpen} onClose={() => setOrderPromptOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{L('Create Production Order', 'Crear orden de produccion')}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {L('Use the same recipe quantity?', '¿Usar la misma cantidad de la receta?')}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {L('Recipe yield', 'Rendimiento receta')}: <strong>{recipe?.yield_qty || 0}</strong>
          </Typography>
          <TextField
            label={L('Other quantity', 'Otra cantidad')}
            type="number"
            fullWidth
            value={customOrderQty}
            onChange={(e) => setCustomOrderQty(e.target.value)}
            inputProps={{ min: 0.01, step: 0.01 }}
            sx={{ mb: 2 }}
          />
          <Typography variant="body2" color="text.secondary">
            {L('Estimated total cost', 'Costo total estimado')}:{' '}
            <strong>
              $
              {(
                Number(breakdown?.costo_por_unidad || 0) *
                Math.max(Number(customOrderQty || 0), 0)
              ).toFixed(2)}
            </strong>
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOrderPromptOpen(false)}>{L('Cancel', 'Cancelar')}</Button>
          <Button
            variant="outlined"
            onClick={() => submitOrderWithQty(Number(recipe?.yield_qty || 1))}
          >
            {L('Same quantity', 'Misma cantidad')}
          </Button>
          <Button
            variant="contained"
            onClick={() => submitOrderWithQty(Number(customOrderQty))}
            disabled={!Number(customOrderQty) || Number(customOrderQty) <= 0}
          >
            {L('Use this quantity', 'Usar esta cantidad')}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}
