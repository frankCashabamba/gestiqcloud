import React from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Typography,
} from '@mui/material'
import type { IngredientMasterRow } from './ingredientCatalog'

export type IngredientInsightMeta = {
  productId: string
  productName: string
  recipeQtyLabel: string
  recipeQtyReference: string | null
  estimatedCost: number
}

type Props = {
  open: boolean
  loading: boolean
  error: string | null
  meta: IngredientInsightMeta | null
  row: IngredientMasterRow | null
  onClose: () => void
  onOpenIngredientMaster: () => void
  onOpenRecipe: (recipeId: string) => void
  dialogPaperSx: object
  dialogActionsSx: object
  sectionCardSx: object
}

export default function RecetaIngredientInsightDialog({
  open,
  loading,
  error,
  meta,
  row,
  onClose,
  onOpenIngredientMaster,
  onOpenRecipe,
  dialogPaperSx,
  dialogActionsSx,
  sectionCardSx,
}: Props) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: dialogPaperSx }}>
      <DialogTitle sx={{ px: 3, py: 2.5, borderBottom: '1px solid #e5e7eb', backgroundImage: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)' }}>
        {meta?.productName || 'Ingrediente'}
      </DialogTitle>
      <DialogContent sx={{ px: 3, py: 3, backgroundColor: '#f8fafc' }}>
        {meta && (
          <Box sx={{ ...sectionCardSx, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              Uso en esta receta
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Cantidad</Typography>
                <Typography variant="body1" sx={{ fontWeight: 700 }}>
                  {meta.recipeQtyLabel}
                </Typography>
                {meta.recipeQtyReference && (
                  <Typography variant="caption" color="text.secondary">
                    Equiv.: {meta.recipeQtyReference}
                  </Typography>
                )}
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Costo estimado en el lote</Typography>
                <Typography variant="body1" sx={{ fontWeight: 700 }}>
                  ${meta.estimatedCost.toFixed(2)}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : error ? (
          <Alert severity="warning" sx={{ borderRadius: 2.5 }}>
            {error}
          </Alert>
        ) : row ? (
          <Box sx={{ ...sectionCardSx, mb: 0 }}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
              {row.inventory_product ? (
                <Chip
                  size="small"
                  color="success"
                  label={`Inventario · ${row.inventory_product.unit || row.unit || '-'}`}
                />
              ) : (
                <Chip size="small" color="warning" label="Sin vinculo de inventario" />
              )}
              {row.hasDivergence && (
                <Chip size="small" color="warning" label="Valores distintos entre recetas" />
              )}
            </Box>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Empaque</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {row.purchase_packaging || '-'}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Contenido</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {row.qty_per_package} {row.package_unit || row.unit || ''}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Costo del pack</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  ${Number(row.package_cost || 0).toFixed(2)}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">Costo por unidad base</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  $
                  {(
                    Number(row.package_cost || 0) /
                    Math.max(Number(row.qty_per_package || 1), 0.0001)
                  ).toFixed(4)} / {row.package_unit || row.unit || '-'}
                </Typography>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              Recetas que lo usan
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {row.refs.map((ref) => (
                <Button
                  key={ref.ingredient_id || ref.recipe_id}
                  variant="outlined"
                  size="small"
                  onClick={() => onOpenRecipe(ref.recipe_id)}
                  sx={{ borderRadius: 999, textTransform: 'none', fontWeight: 600 }}
                >
                  {ref.recipe_name} · {Number(ref.qty || 0).toFixed(2)} {ref.unit || ''}
                </Button>
              ))}
            </Box>
          </Box>
        ) : (
          <Alert severity="info" sx={{ borderRadius: 2.5 }}>
            No se encontro una ficha maestra para este ingrediente.
          </Alert>
        )}
      </DialogContent>
      <DialogActions sx={dialogActionsSx}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button onClick={onClose} sx={{ borderRadius: 2.5, color: '#475569', fontWeight: 600 }}>
            Cerrar
          </Button>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            onClick={onOpenIngredientMaster}
            disabled={!meta?.productId}
            sx={{ borderRadius: 2.5, fontWeight: 600 }}
          >
            Abrir en ingredientes
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  )
}
