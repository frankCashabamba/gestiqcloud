/**
 * RecetaForm - Formulario de creación/edición de recetas
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom'
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

export default function RecetaForm({ open, recipe, onClose }: RecetaFormProps) {
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

      if (recipe.ingredients) {
        setIngredientes(recipe.ingredients.map(ing => ({
          product_id: ing.product_id,
          qty: ing.qty,
          unit: ing.unit,
          purchase_packaging: ing.purchase_packaging,
          qty_per_package: ing.qty_per_package,
          package_unit: ing.package_unit,
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
        updated[index].package_unit = producto.unit || 'kg';

        // Valores por defecto según la unidad
        const defaultPresentaciones: Record<string, { qty: number, desc: string }> = {
          'kg': { qty: 50, desc: 'Saco 50 kg' },
          'lb': { qty: 50, desc: 'Saco 50 lb' },
          'g': { qty: 1000, desc: 'Bolsa 1 kg' },
          'oz': { qty: 16, desc: 'Libra (16 oz)' },
          'L': { qty: 20, desc: 'Bidón 20 L' },
          'unit': { qty: 24, desc: 'Caja 24 unidades' },
          'unidades': { qty: 24, desc: 'Caja 24 unidades' }
        };

        const unit = (producto.unit || 'kg').toLowerCase();
        const defaultPres = defaultPresentaciones[unit] || { qty: 1, desc: 'Unidad' };

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
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogContent>
          <Box display="flex" justifyContent="center" alignItems="center" p={4}>
            <Typography>Cargando productos...</Typography>
          </Box>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>
          {recipe ? 'Editar Receta' : 'Nueva Receta'}
        </DialogTitle>

        <DialogContent dividers>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* Datos básicos */}
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Nombre de Receta"
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
                  <TextField {...params} label="Producto Final" required />
                )}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
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

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Tiempo (min)"
                value={prepTimeMinutes || ''}
                onChange={(e) => setPrepTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
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

          {/* Ingredientes */}
          <Divider sx={{ my: 3 }} />

          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Ingredientes</Typography>
            <Button
              size="small"
              startIcon={<Add />}
              onClick={handleAddIngredient}
            >
              Agregar
            </Button>
          </Box>

          {ingredientes.map((ing, index) => (
            <Box key={index} mb={2} p={2} sx={{ bgcolor: 'grey.50', borderRadius: 1 }}>
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
                    label="Unidad"
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
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {loading ? 'Guardando...' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
