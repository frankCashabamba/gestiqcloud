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
  const [nombre, setNombre] = useState('');
  const [productId, setProductId] = useState<string | null>(null);
  const [rendimiento, setRendimiento] = useState<number>(1);
  const [tiempoPreparacion, setTiempoPreparacion] = useState<number | null>(null);
  const [instrucciones, setInstrucciones] = useState('');

  // Ingredientes
  const [ingredientes, setIngredientes] = useState<RecipeIngredient[]>([]);

  // Cargar productos
  useEffect(() => {
    loadProducts();
  }, []);

  // Cargar datos de receta si es edición
  useEffect(() => {
    if (recipe) {
      setNombre(recipe.name);
      setProductId(recipe.product_id);
      setRendimiento(recipe.rendimiento);
      setTiempoPreparacion(recipe.tiempo_preparacion || null);
      setInstrucciones(recipe.instrucciones || '');

      if (recipe.ingredientes) {
        setIngredientes(recipe.ingredientes.map(ing => ({
          producto_id: ing.producto_id,
          qty: ing.qty,
          unidad_medida: ing.unidad_medida,
          presentacion_compra: ing.presentacion_compra,
          qty_presentacion: ing.qty_presentacion,
          unidad_presentacion: ing.unidad_presentacion,
          costo_presentacion: ing.costo_presentacion,
          notas: ing.notas,
          orden: ing.orden || 0
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
        producto_id: '',
        qty: 0,
        unidad_medida: 'kg',
        presentacion_compra: '',
        qty_presentacion: 0,
        unidad_presentacion: 'kg',
        costo_presentacion: 0,
        orden: ingredientes.length
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
    if (field === 'producto_id' && value) {
      const producto = products.find(p => p.id === value);
      if (producto) {
        // Autocompletar con valores del producto
        updated[index].unidad_medida = producto.unit || 'kg';
        updated[index].unidad_presentacion = producto.unit || 'kg';

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

        updated[index].qty_presentacion = defaultPres.qty;
        updated[index].presentacion_compra = defaultPres.desc;
        // Costo: usar cost_price si existe, sino dejar en 0 para que el usuario lo ingrese
        updated[index].costo_presentacion = producto.cost_price ?
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

    if (rendimiento <= 0) {
      setError('Yield must be greater than 0');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = {
        name: nombre,
        product_id: productId,
        rendimiento,
        tiempo_preparacion: tiempoPreparacion || undefined,
        instrucciones: instrucciones || undefined,
        ingredientes: ingredientes.filter(ing => ing.producto_id && ing.qty > 0)
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
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
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
                value={rendimiento}
                onChange={(e) => setRendimiento(Number(e.target.value))}
                required
                inputProps={{ min: 1 }}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                type="number"
                label="Tiempo (min)"
                value={tiempoPreparacion || ''}
                onChange={(e) => setTiempoPreparacion(e.target.value ? Number(e.target.value) : null)}
                inputProps={{ min: 0 }}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Instrucciones"
                value={instrucciones}
                onChange={(e) => setInstrucciones(e.target.value)}
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
                    value={products.find(p => p.id === ing.producto_id) || null}
                    onChange={(_, val) => handleIngredientChange(index, 'producto_id', val?.id || '')}
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
                    value={ing.unidad_medida}
                    onChange={(e) => handleIngredientChange(index, 'unidad_medida', e.target.value)}
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    size="small"
                    fullWidth
                    label="Presentación (ej: Saco 110 lbs)"
                    value={ing.presentacion_compra}
                    onChange={(e) => handleIngredientChange(index, 'presentacion_compra', e.target.value)}
                  />
                </Grid>

                <Grid item xs={4} sm={2}>
                  <TextField
                    size="small"
                    fullWidth
                    type="number"
                    label="Cant. Present."
                    value={ing.qty_presentacion}
                    onChange={(e) => handleIngredientChange(index, 'qty_presentacion', Number(e.target.value))}
                  />
                </Grid>

                <Grid item xs={4} sm={2}>
                  <TextField
                    size="small"
                    fullWidth
                    label="Unidad Pres."
                    value={ing.unidad_presentacion}
                    onChange={(e) => handleIngredientChange(index, 'unidad_presentacion', e.target.value)}
                  />
                </Grid>

                <Grid item xs={4} sm={3}>
                  <TextField
                    size="small"
                    fullWidth
                    type="number"
                    label="Costo Present."
                    value={ing.costo_presentacion}
                    onChange={(e) => handleIngredientChange(index, 'costo_presentacion', Number(e.target.value))}
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
