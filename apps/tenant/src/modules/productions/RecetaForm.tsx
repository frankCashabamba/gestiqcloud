/**
 * RecetaForm - Formulario de creación/edición de recetas
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Grid, Box, Typography, IconButton,
  Autocomplete, Divider, Alert
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import {
  createRecipe, updateRecipe, type Recipe, type RecipeIngredient
} from '../../services/api/recetas';
import { listProducts, type Product } from '../../services/api/products';

interface RecetaFormProps {
  open: boolean;
  recipe?: Recipe | null;
  onClose: () => void;
}

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

const formDialogPaperSx = {
  borderRadius: 4,
  border: '1px solid #e2e8f0',
  backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)',
  boxShadow: '0 28px 80px rgba(15, 23, 42, 0.16)',
};

const formSectionSx = {
  mb: 3,
  p: { xs: 2, md: 2.5 },
  borderRadius: 3,
  border: '1px solid #e7edf5',
  backgroundColor: '#ffffff',
  boxShadow: '0 12px 32px rgba(15, 23, 42, 0.05)',
};

const formFieldGroupSx = {
  '& .MuiTextField-root': {
    '& .MuiOutlinedInput-root': {
      borderRadius: 2.5,
      backgroundColor: '#ffffff',
    },
    '& .MuiInputLabel-root': {
      fontWeight: 500,
    },
  },
  '& .MuiAutocomplete-root .MuiOutlinedInput-root': {
    borderRadius: 2.5,
    backgroundColor: '#ffffff',
  },
};

const formActionsSx = {
  px: { xs: 2, md: 3 },
  py: 2,
  gap: 1,
  borderTop: '1px solid #e5e7eb',
  backgroundColor: 'rgba(255,255,255,0.94)',
  backdropFilter: 'blur(10px)',
};

export default function RecetaForm({ open, recipe, onClose }: RecetaFormProps) {
  const { t } = useTranslation(['productions', 'common']);
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);

  // Datos de receta
  const [name, setName] = useState('');
  const [productId, setProductId] = useState<string | null>(null);
  const [yieldQty, setYieldQty] = useState<number>(1);
  const [prepTimeMinutes, setPrepTimeMinutes] = useState<number | null>(null);
  const [instructions, setInstructions] = useState('');

  // Tiempos y producción
  const [bakingTimeMinutes, setBakingTimeMinutes] = useState<number | null>(null);
  const [ovenTempCelsius, setOvenTempCelsius] = useState<number | null>(null);
  const [restTimeMinutes, setRestTimeMinutes] = useState<number | null>(null);
  const [touchMinutesStandard, setTouchMinutesStandard] = useState<number | null>(null);
  const [ovenMinutesStandard, setOvenMinutesStandard] = useState<number | null>(null);
  const [processMinutes, setProcessMinutes] = useState<number | null>(null);
  const [wastePct, setWastePct] = useState<number | null>(null);
  const [traysPerBatch, setTraysPerBatch] = useState<number | null>(null);
  const [unitsPerTray, setUnitsPerTray] = useState<number | null>(null);

  // Ingredientes
  const [ingredientes, setIngredientes] = useState<RecipeIngredient[]>([]);

  // Cargar productos
  useEffect(() => {
    loadProducts();
  }, []);

  // Cargar datos de receta si es edición
  useEffect(() => {
    if (recipe) {
      setName(recipe.name);
      setProductId(recipe.product_id);
      setYieldQty(recipe.yield_qty);
      setPrepTimeMinutes(recipe.prep_time_minutes || null);
      setInstructions(recipe.instructions || '');
      setBakingTimeMinutes((recipe as any).baking_time_minutes ?? null);
      setOvenTempCelsius((recipe as any).oven_temp_celsius ?? null);
      setRestTimeMinutes((recipe as any).rest_time_minutes ?? null);
      setTouchMinutesStandard((recipe as any).touch_minutes_standard ?? null);
      setOvenMinutesStandard((recipe as any).oven_minutes_standard ?? null);
      setProcessMinutes((recipe as any).process_minutes ?? null);
      setWastePct((recipe as any).waste_pct ?? null);
      setTraysPerBatch((recipe as any).trays_per_batch ?? null);
      setUnitsPerTray((recipe as any).units_per_tray ?? null);

      if (recipe.ingredients) {
        setIngredientes(recipe.ingredients.map(ing => ({
          product_id: ing.product_id,
          qty: ing.qty,
          unit: normalizeRecipeUnit(ing.unit),
          purchase_packaging: ing.purchase_packaging,
          qty_per_package: ing.qty_per_package,
          package_unit: normalizeRecipeUnit(ing.package_unit),
          package_cost: ing.package_cost,
          notes: ing.notes,
          line_order: ing.line_order || 0
        })));
      }
    }
  }, [recipe]);

  // Preseleccionar producto si viene de query param
  useEffect(() => {
    if (!recipe) {
      const pid = searchParams.get('productId')
      if (pid) setProductId(pid)
    }
  }, [recipe, searchParams])

  const loadProducts = async () => {
    try {
      const data = await listProducts({ limit: 500 });
      setProducts(data);
    } catch (err: any) {
      console.error('Error cargando productos:', err);
    }
  };

  const handleAddIngredient = () => {
    setIngredientes([
      ...ingredientes,
      {
        product_id: '',
        qty: 0,
        unit: 'kg',
        purchase_packaging: '',
        qty_per_package: 0,
        package_unit: 'kg',
        package_cost: 0,
        line_order: ingredientes.length
      }
    ]);
  };

  const handleRemoveIngredient = (index: number) => {
    setIngredientes(ingredientes.filter((_, i) => i !== index));
  };

  const handleIngredientChange = (index: number, field: string, value: any) => {
    const updated = [...ingredientes];
    (updated[index] as any)[field] = value;

    // Si se selecciona un producto, autocompletar datos de compra
    if (field === 'product_id' && value) {
      const producto = products.find(p => p.id === value);
      if (producto) {
        // Autocompletar con valores del producto
        updated[index].unit = producto.unit || 'kg';
        updated[index].unit = normalizeRecipeUnit(producto.unit);
        updated[index].package_unit = normalizeRecipeUnit(producto.unit);

        // Valores por defecto según la unidad
        const defaultPresentaciones: Record<string, { qty: number, desc: string }> = {
          'kg': { qty: 50, desc: 'Saco 50 kg' },
          'lb': { qty: 50, desc: 'Saco 50 lb' },
          'g': { qty: 1000, desc: 'Bolsa 1 kg' },
          'oz': { qty: 16, desc: 'Libra (16 oz)' },
          'L': { qty: 20, desc: 'Bidón 20 L' },
          'unit': { qty: 24, desc: t('productions:recipeForm.box24Units') },
          'unidades': { qty: 24, desc: t('productions:recipeForm.box24Units') }
        };

        const unit = normalizeRecipeUnit(producto.unit);
        const defaultPres = defaultPresentaciones[unit] || { qty: 1, desc: t('productions:recipeForm.unit') };

        updated[index].qty_per_package = defaultPres.qty;
        updated[index].purchase_packaging = defaultPres.desc;
        // Costo: usar cost_price si existe, sino dejar en 0 para que el usuario lo ingrese
        updated[index].package_cost = producto.cost_price ?
          Number(producto.cost_price) * defaultPres.qty : 0;
      }
    }

    setIngredientes(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!productId) {
      setError('Must select a product');
      return;
    }

    if (yieldQty <= 0) {
      setError('Yield must be greater than 0');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = {
        name,
        product_id: productId,
        yield_qty: yieldQty,
        prep_time_minutes: prepTimeMinutes || undefined,
        baking_time_minutes: bakingTimeMinutes ?? undefined,
        oven_temp_celsius: ovenTempCelsius ?? undefined,
        rest_time_minutes: restTimeMinutes ?? undefined,
        touch_minutes_standard: touchMinutesStandard ?? undefined,
        oven_minutes_standard: ovenMinutesStandard ?? undefined,
        process_minutes: Math.max((prepTimeMinutes || 0) - (touchMinutesStandard || 0), 0) || undefined,
        waste_pct: wastePct ?? undefined,
        trays_per_batch: traysPerBatch ?? undefined,
        units_per_tray: unitsPerTray ?? undefined,
        instructions: instructions || undefined,
        ingredients: ingredientes.filter(ing => ing.product_id && ing.qty > 0)
      };

      if (recipe) {
        // Actualizar (ahora incluye ingredientes)
        await updateRecipe(recipe.id, data);
      } else {
        // Crear
        await createRecipe(data);
      }

      onClose();
    } catch (err: any) {
      setError(err.message || 'Error saving recipe');
    } finally {
      setLoading(false);
    }
  };

  // Si no tenemos productos aún, mostrar cargando
  if (open && products.length === 0) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: formDialogPaperSx }}>
        <DialogContent sx={{ px: 3, py: 4, backgroundColor: '#f8fafc' }}>
          <Box display="flex" justifyContent="center" alignItems="center" p={4}>
            <Typography>Loading products...</Typography>
          </Box>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth PaperProps={{ sx: formDialogPaperSx }}>
      <form onSubmit={handleSubmit}>
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
            {recipe ? t('productions:recipeForm.editRecipe') : t('productions:recipeForm.newRecipe')}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Define producto, rendimiento e ingredientes con una estructura mas clara.
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
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* Datos básicos */}
          <Box sx={{ ...formSectionSx, ...formFieldGroupSx }}>
            <Typography variant="overline" sx={{ color: '#64748b', letterSpacing: 1.2 }}>
              Base de la receta
            </Typography>
            <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label={t('productions:recipeForm.recipeName')}
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Autocomplete
                options={products}
                getOptionLabel={(opt) => opt.name}
                value={products.find(p => p.id === productId) || null}
                onChange={(_, val) => setProductId(val?.id || null)}
                renderInput={(params) => (
                  <TextField {...params} label={t('productions:recipeForm.finalProduct')} required />
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Rendimiento (uds)"
                value={yieldQty}
                onChange={(e) => setYieldQty(Number(e.target.value))}
                required
                inputProps={{ min: 1 }}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Instrucciones"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
            </Grid>
            </Grid>
          </Box>

          {/* Tiempos y Producción */}
          <Box sx={{ ...formSectionSx, ...formFieldGroupSx }}>
            <Typography variant="overline" sx={{ color: '#64748b', letterSpacing: 1.2 }}>
              Produccion
            </Typography>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>Tiempos y Produccion</Typography>

          <Grid container spacing={2}>
            {/* Row 1: Tiempos */}
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Preparación (min)"
                value={prepTimeMinutes ?? ''}
                onChange={(e) => setPrepTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Horneado (min)"
                value={bakingTimeMinutes ?? ''}
                onChange={(e) => setBakingTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Temperatura horno °C"
                value={ovenTempCelsius ?? ''}
                onChange={(e) => setOvenTempCelsius(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Reposo/Fermentación (min)"
                value={restTimeMinutes ?? ''}
                onChange={(e) => setRestTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>

            {/* Row 2: TOUCH vs PROCESO */}
            <Grid item xs={12}>
              <Alert severity="info" sx={{ py: 0.5, borderRadius: 2.5, backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', '& .MuiAlert-icon': { color: '#2563eb' } }}>
                🟢 Touch = trabajo activo (cuesta MO) | ⚫ Proceso = pasivo (fermentación/reposo)
              </Alert>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Trabajo activo min (TOUCH)"
                value={touchMinutesStandard ?? ''}
                onChange={(e) => setTouchMinutesStandard(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
                helperText="Pesar, amasar, bolear, cargar/descargar"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Proceso pasivo (min)"
                value={Math.max((prepTimeMinutes || 0) - (touchMinutesStandard || 0), 0) || ''}
                InputProps={{ readOnly: true }}
                inputProps={{ min: 0 }}
                helperText={t('productions:recipeForm.autoHelperText')}
              />
            </Grid>

            {/* Row 3: Producción */}
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Merma %"
                value={wastePct ?? ''}
                onChange={(e) => setWastePct(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0, max: 100, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Bandejas por lote"
                value={traysPerBatch ?? ''}
                onChange={(e) => setTraysPerBatch(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label={t('productions:recipeForm.unitsPerTray')}
                value={unitsPerTray ?? ''}
                onChange={(e) => setUnitsPerTray(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>
          </Grid>
          </Box>

          {/* Ingredientes */}
          <Box sx={{ ...formSectionSx, ...formFieldGroupSx }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Ingredientes</Typography>
            <Button
              size="small"
              startIcon={<Add />}
              onClick={handleAddIngredient}
              sx={{ borderRadius: 2.5, fontWeight: 600 }}
            >
              Agregar
            </Button>
          </Box>

          {ingredientes.map((ing, index) => (
            <Box key={index} mb={2} p={2} sx={{ bgcolor: '#f8fafc', borderRadius: 2.5, border: '1px solid #e2e8f0' }}>
              <Grid container spacing={1.5}>
                <Grid item xs={12} sm={6}>
                  <Autocomplete
                    size="small"
                    options={products}
                    getOptionLabel={(opt) => opt.name}
                    value={products.find(p => p.id === ing.product_id) || null}
                    onChange={(_, val) => handleIngredientChange(index, 'product_id', val?.id || '')}
                    renderInput={(params) => (
                      <TextField {...params} label="Product" />
                    )}
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    size="small"
                    fullWidth
                    type="number"
                    label="Quantity"
                    value={ing.qty}
                    onChange={(e) => handleIngredientChange(index, 'qty', Number(e.target.value))}
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    size="small"
                    fullWidth
                    label={t('productions:recipeForm.unit')}
                    value={ing.unit}
                    onChange={(e) => handleIngredientChange(index, 'unit', e.target.value)}
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    size="small"
                    fullWidth
                    label="Presentación (ej: Saco 110 lbs)"
                    value={ing.purchase_packaging}
                    onChange={(e) => handleIngredientChange(index, 'purchase_packaging', e.target.value)}
                  />
                </Grid>

                <Grid item xs={4} sm={2}>
                  <TextField
                    size="small"
                    fullWidth
                    type="number"
                    label="Cant. Present."
                    value={ing.qty_per_package}
                    onChange={(e) => handleIngredientChange(index, 'qty_per_package', Number(e.target.value))}
                  />
                </Grid>

                <Grid item xs={4} sm={2}>
                  <TextField
                    size="small"
                    fullWidth
                    label="Unidad Pres."
                    value={ing.package_unit}
                    onChange={(e) => handleIngredientChange(index, 'package_unit', e.target.value)}
                  />
                </Grid>

                <Grid item xs={4} sm={3}>
                  <TextField
                    size="small"
                    fullWidth
                    type="number"
                    label="Costo Present."
                    value={ing.package_cost}
                    onChange={(e) => handleIngredientChange(index, 'package_cost', Number(e.target.value))}
                    InputProps={{ startAdornment: '$' }}
                  />
                </Grid>

                <Grid item xs={12} sm={1}>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleRemoveIngredient(index)}
                  >
                    <Delete />
                  </IconButton>
                </Grid>
              </Grid>
            </Box>
          ))}
          </Box>
        </DialogContent>

        <DialogActions sx={formActionsSx}>
          <Button onClick={onClose} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading} sx={{ borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}>
            {loading ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
