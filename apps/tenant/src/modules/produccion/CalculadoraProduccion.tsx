/**
 * CalculadoraProduccion - Calculadora de materiales para producción
 */

import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  TextField, Typography, Box, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, Alert, Grid, Chip
} from '@mui/material';
import { calculateProduction, type Recipe, type ProductionCalculation } from '../../services/api/recetas';

interface CalculadoraProduccionProps {
  open: boolean;
  recipe: Recipe;
  onClose: () => void;
}

export default function CalculadoraProduccion({ open, recipe, onClose }: CalculadoraProduccionProps) {
  const [qtyToProduce, setQtyToProduce] = useState<number>(recipe.rendimiento);
  const [workers, setWorkers] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProductionCalculation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCalculate = async () => {
    if (qtyToProduce <= 0) {
      setError('Cantidad debe ser mayor a 0');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const data = await calculateProduction(recipe.id, qtyToProduce, workers);
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Error al calcular');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Calcular Producción: {recipe.name}
      </DialogTitle>

      <DialogContent dividers>
        {/* Inputs */}
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              type="number"
              label="Cantidad a Producir"
              value={qtyToProduce}
              onChange={(e) => setQtyToProduce(Number(e.target.value))}
              inputProps={{ min: 1 }}
              helperText={`Rendimiento base: ${recipe.rendimiento} uds`}
            />
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              type="number"
              label="Trabajadores"
              value={workers}
              onChange={(e) => setWorkers(Number(e.target.value))}
              inputProps={{ min: 1 }}
            />
          </Grid>

          <Grid item xs={12}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleCalculate}
              disabled={loading}
            >
              {loading ? 'Calculando...' : 'Calcular'}
            </Button>
          </Grid>
        </Grid>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Resultados */}
        {result && (
          <Box>
            {/* Resumen */}
            <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'primary.50' }}>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Batches
                  </Typography>
                  <Typography variant="h6">
                    {result.batches_required.toFixed(1)}
                  </Typography>
                </Grid>

                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Costo Total
                  </Typography>
                  <Typography variant="h6">
                    ${result.costo_total_produccion.toFixed(2)}
                  </Typography>
                </Grid>

                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Costo/Unidad
                  </Typography>
                  <Typography variant="h6">
                    ${result.costo_por_unidad.toFixed(4)}
                  </Typography>
                </Grid>

                {result.tiempo_estimado && (
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Tiempo Estimado
                    </Typography>
                    <Typography variant="h6">
                      {result.tiempo_estimado.tiempo_total_horas.toFixed(1)}h
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Paper>

            {/* Tabla de ingredientes */}
            <Typography variant="h6" gutterBottom>
              Materiales Necesarios
            </Typography>

            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ingrediente</TableCell>
                    <TableCell align="right">Necesario</TableCell>
                    <TableCell align="right">Comprar</TableCell>
                    <TableCell>Presentación</TableCell>
                    <TableCell align="right">Costo Est.</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.ingredientes.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>{item.producto}</TableCell>
                      <TableCell align="right">
                        {item.qty_necesaria.toFixed(2)} {item.unidad}
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={`${item.presentaciones_necesarias}x`}
                          size="small"
                          color="primary"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {item.presentacion_compra}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <strong>${item.costo_estimado.toFixed(2)}</strong>
                      </TableCell>
                    </TableRow>
                  ))}
                  
                  {/* Total */}
                  <TableRow>
                    <TableCell colSpan={4} align="right">
                      <strong>TOTAL</strong>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="h6" color="primary">
                        ${result.costo_total_produccion.toFixed(2)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cerrar</Button>
        {result && (
          <Button variant="contained" onClick={() => alert('Crear Orden de Compra')}>
            Crear Orden de Compra
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
