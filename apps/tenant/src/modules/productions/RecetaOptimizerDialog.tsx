import React from 'react'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { AutoFixHigh } from '@mui/icons-material'
import type { Product } from '../../services/api/products'
import type { RecipeOptimizationResponse } from '../../services/api/recetas'

type IngredientDraft = {
  product_id: string
}

type Props = {
  open: boolean
  canWrite: boolean
  optimizing: boolean
  optimizerError: string | null
  optimizerResult: RecipeOptimizationResponse | null
  optimizerSellingPrice: string
  optimizerTargetMargin: string
  optimizerMaxChanges: string
  optimizerConstraints: string
  optimizerLockedIds: string[]
  ingredientsDraft: IngredientDraft[]
  products: Product[]
  onChangeSellingPrice: (value: string) => void
  onChangeTargetMargin: (value: string) => void
  onChangeMaxChanges: (value: string) => void
  onChangeConstraints: (value: string) => void
  onToggleLockedIngredient: (productId: string) => void
  onClose: () => void
  onRun: () => void
  onApply: () => void
  dialogPaperSx: object
  dialogActionsSx: object
  sectionCardSx: object
  metricCardSx: object
  tableContainerSx: object
}

export default function RecetaOptimizerDialog({
  open,
  canWrite,
  optimizing,
  optimizerError,
  optimizerResult,
  optimizerSellingPrice,
  optimizerTargetMargin,
  optimizerMaxChanges,
  optimizerConstraints,
  optimizerLockedIds,
  ingredientsDraft,
  products,
  onChangeSellingPrice,
  onChangeTargetMargin,
  onChangeMaxChanges,
  onChangeConstraints,
  onToggleLockedIngredient,
  onClose,
  onRun,
  onApply,
  dialogPaperSx,
  dialogActionsSx,
  sectionCardSx,
  metricCardSx,
  tableContainerSx,
}: Props) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: dialogPaperSx }}>
      <DialogTitle sx={{ px: 3, py: 2.5, borderBottom: '1px solid #e5e7eb', backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)' }}>
        Optimizacion de receta con IA
      </DialogTitle>
      <DialogContent sx={{ px: 3, py: 3, backgroundColor: '#f8fafc' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Usa costes actuales y restricciones operativas para proponer una version mas eficiente de la receta.
        </Typography>

        {optimizerError && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2.5 }}>
            {optimizerError}
          </Alert>
        )}

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Precio de venta"
              type="number"
              fullWidth
              size="small"
              value={optimizerSellingPrice}
              onChange={(e) => onChangeSellingPrice(e.target.value)}
              inputProps={{ min: 0, step: 0.01 }}
              helperText="Opcional, para recalcular margen"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Margen objetivo %"
              type="number"
              fullWidth
              size="small"
              value={optimizerTargetMargin}
              onChange={(e) => onChangeTargetMargin(e.target.value)}
              inputProps={{ min: 0, max: 100, step: 0.1 }}
              helperText="Opcional"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Max. ingredientes a cambiar"
              type="number"
              fullWidth
              size="small"
              value={optimizerMaxChanges}
              onChange={(e) => onChangeMaxChanges(e.target.value)}
              inputProps={{ min: 1, max: 20, step: 1 }}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Restricciones"
              fullWidth
              size="small"
              multiline
              minRows={3}
              value={optimizerConstraints}
              onChange={(e) => onChangeConstraints(e.target.value)}
              placeholder="Ej.: no tocar harina madre, mantener textura crujiente, no bajar rendimiento, evitar cambios >5% en sal."
            />
          </Grid>
        </Grid>

        <Box sx={{ ...sectionCardSx, mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
            Ingredientes bloqueados
          </Typography>
          <Grid container spacing={0.5}>
            {ingredientsDraft.length === 0 ? (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">No hay ingredientes cargados.</Typography>
              </Grid>
            ) : (
              ingredientsDraft.map((item) => {
                const product = products.find((p) => p.id === item.product_id)
                const label = product?.name || item.product_id
                return (
                  <Grid item xs={12} sm={6} key={item.product_id}>
                    <FormControlLabel
                      control={(
                        <Checkbox
                          size="small"
                          checked={optimizerLockedIds.includes(item.product_id)}
                          onChange={() => onToggleLockedIngredient(item.product_id)}
                        />
                      )}
                      label={<Typography variant="body2">{label}</Typography>}
                    />
                  </Grid>
                )
              })
            )}
          </Grid>
        </Box>

        {optimizerResult && (
          <Box sx={{ ...sectionCardSx, mb: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.75 }}>
              Propuesta optimizada
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {optimizerResult.summary}
            </Typography>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={4}>
                <Box sx={metricCardSx}>
                  <Typography variant="caption" color="text.secondary">Costo actual / u</Typography>
                  <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700 }}>
                    ${Number(optimizerResult.current.full_cost_unit || 0).toFixed(4)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Margen: {optimizerResult.current.margin_pct != null ? `${Number(optimizerResult.current.margin_pct).toFixed(2)}%` : 'n/d'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={metricCardSx}>
                  <Typography variant="caption" color="text.secondary">Costo optimizado / u</Typography>
                  <Typography variant="h6" color="success.main" sx={{ mt: 0.5, fontWeight: 700 }}>
                    ${Number(optimizerResult.optimized.full_cost_unit || 0).toFixed(4)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Margen: {optimizerResult.optimized.margin_pct != null ? `${Number(optimizerResult.optimized.margin_pct).toFixed(2)}%` : 'n/d'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={metricCardSx}>
                  <Typography variant="caption" color="text.secondary">Ahorro estimado</Typography>
                  <Typography variant="h6" color={optimizerResult.savings_total >= 0 ? 'success.main' : 'error.main'} sx={{ mt: 0.5, fontWeight: 700 }}>
                    ${Number(optimizerResult.savings_total || 0).toFixed(2)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {Number(optimizerResult.savings_pct || 0).toFixed(2)}% del lote
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {optimizerResult.warnings.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2, borderRadius: 2.5 }}>
                {optimizerResult.warnings.join(' ')}
              </Alert>
            )}

            {optimizerResult.assumptions.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
                  Supuestos
                </Typography>
                {optimizerResult.assumptions.map((item, idx) => (
                  <Typography key={idx} variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                    {`• ${item}`}
                  </Typography>
                ))}
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              Cambios sugeridos
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={tableContainerSx}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ingrediente</TableCell>
                    <TableCell align="right">Actual</TableCell>
                    <TableCell align="right">Sugerido</TableCell>
                    <TableCell align="right">Impacto</TableCell>
                    <TableCell>Motivo</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {optimizerResult.changes.map((change, idx) => (
                    <TableRow key={`${change.product_id}-${change.line_order ?? idx}-${idx}`}>
                      <TableCell>{change.product_name}</TableCell>
                      <TableCell align="right">{Number(change.current_qty || 0).toFixed(4)} {change.unit}</TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={change.change_type === 'adjust_qty' ? 'success.main' : 'text.primary'}
                          sx={{ fontWeight: change.change_type === 'adjust_qty' ? 700 : 400 }}
                        >
                          {Number(change.suggested_qty || 0).toFixed(4)} {change.unit}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        ${Number(change.estimated_cost_delta || 0).toFixed(2)}
                      </TableCell>
                      <TableCell>{change.rationale || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={dialogActionsSx}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button onClick={onClose} disabled={optimizing} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>
            Cerrar
          </Button>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {optimizerResult && canWrite && (
            <Button
              variant="contained"
              color="primary"
              onClick={onApply}
              disabled={optimizing}
              sx={{ borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
            >
              {optimizing ? <CircularProgress size={16} color="inherit" /> : 'Aplicar propuesta'}
            </Button>
          )}
          <Button
            variant="contained"
            color="secondary"
            onClick={onRun}
            disabled={optimizing}
            startIcon={optimizing ? undefined : <AutoFixHigh />}
            sx={{ borderRadius: 2.5, fontWeight: 700, boxShadow: 'none' }}
          >
            {optimizing ? <CircularProgress size={16} color="inherit" /> : 'Analizar con IA'}
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  )
}
