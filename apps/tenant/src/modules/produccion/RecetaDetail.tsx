/**
 * RecetaDetail - Vista detallada de receta con desglose de costos
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Typography, Box, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Divider, Alert, CircularProgress, Grid
} from '@mui/material';
import { getRecipe, getCostBreakdown, type Recipe, type CostBreakdown } from '../../services/api/recetas';
import tenantApi from '../../shared/api/client';

interface RecetaDetailProps {
  open: boolean;
  recipeId: string;
  onClose: () => void;
  onCreateOrder?: (recipe: Recipe) => void;
}

export default function RecetaDetail({ open, recipeId, onClose, onCreateOrder }: RecetaDetailProps) {
  const [loading, setLoading] = useState(true);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

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
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProductPrice = async (multiplier: number = 2.5) => {
    if (!recipe || !breakdown) return;

    try {
      setUpdating(true);
      const newPrice = breakdown.costo_por_unidad * multiplier;

      await tenantApi.put(`/api/v1/tenant/products/${recipe.product_id}`, {
        price: Number(newPrice.toFixed(2)),
        cost_price: Number(breakdown.costo_por_unidad.toFixed(4))
      });

      alert(`Precio actualizado a $${newPrice.toFixed(2)} (margen ${((multiplier - 1) * 100).toFixed(0)}%)`);
    } catch (err: any) {
      alert('Error al actualizar precio: ' + (err.message || 'Unknown error'));
    } finally {
      setUpdating(false);
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
          <Alert severity="error">{error || 'No se pudo cargar la receta'}</Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    );
  }

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
                Rendimiento
              </Typography>
              <Typography variant="h6">{recipe.yield_qty} uds</Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                Costo Total
              </Typography>
              <Typography variant="h6">${breakdown.costo_total.toFixed(2)}</Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                Costo/Unidad
              </Typography>
              <Typography variant="h6">${breakdown.costo_por_unidad.toFixed(4)}</Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                Ingredientes
              </Typography>
              <Typography variant="h6">{breakdown.ingredientes_count}</Typography>
            </Grid>
          </Grid>
        </Box>

        {/* Tiempo de preparación */}
        {recipe.prep_time_minutes && (
          <Box mb={2}>
            <Chip label={`⏱️ ${recipe.prep_time_minutes} minutos`} color="primary" />
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Desglose de ingredientes */}
        <Typography variant="h6" gutterBottom>
          Desglose de Ingredientes
        </Typography>

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ingrediente</TableCell>
                <TableCell align="right">Cantidad</TableCell>
                <TableCell>Presentación</TableCell>
                <TableCell align="right">Costo</TableCell>
                <TableCell align="right">% Costo</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {breakdown.desglose.map((item, index) => (
                <TableRow key={index}>
                  <TableCell>{item.producto}</TableCell>
                  <TableCell align="right">
                    {item.qty.toFixed(2)} {item.unidad}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {item.presentacion_compra}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <strong>${item.costo.toFixed(2)}</strong>
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={`${item.porcentaje.toFixed(1)}%`}
                      size="small"
                      color={item.porcentaje > 30 ? 'error' : item.porcentaje > 15 ? 'warning' : 'default'}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Instrucciones */}
        {recipe.instructions && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              Instrucciones
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {recipe.instructions}
            </Typography>
          </>
        )}
      </DialogContent>

      <DialogActions>
        {onCreateOrder && recipe && (
          <Button
            variant="contained"
            color="primary"
            onClick={() => onCreateOrder(recipe)}
            disabled={updating}
          >
            Nueva Orden
          </Button>
        )}
        <Button onClick={onClose}>Cerrar</Button>
      </DialogActions>
    </Dialog>
  );
}
