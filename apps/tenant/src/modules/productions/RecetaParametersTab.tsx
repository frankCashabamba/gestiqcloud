import React from 'react'
import {
  Alert,
  Box,
  Chip,
  Grid,
  TextField,
  Typography,
} from '@mui/material'
import type { Recipe } from '../../services/api/recetas'

type ProdParams = {
  prep_time_minutes: number | null
  baking_time_minutes: number | null
  oven_temp_celsius: number | null
  rest_time_minutes: number | null
  touch_minutes_standard: number | null
  oven_minutes_standard: number | null
  process_minutes: number | null
  waste_pct: number | null
  overhead_pct: number | null
  trays_per_batch: number | null
  units_per_tray: number | null
  instructions: string
}

type Props = {
  t: (key: string, options?: any) => string
  isEditing: boolean
  recipe: Recipe
  prodParams: ProdParams
  fieldGroupSx: object
  infoAlertSx: object
  onSetProdParams: React.Dispatch<React.SetStateAction<ProdParams>>
}

export default function RecetaParametersTab({
  t,
  isEditing,
  recipe,
  prodParams,
  fieldGroupSx,
  infoAlertSx,
  onSetProdParams,
}: Props) {
  return (
    <Box>
      {isEditing ? (
        <Box sx={fieldGroupSx}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              {t('productions:recipe.productionParameters')}
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.prepTime')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.prep_time_minutes ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, prep_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.bakingTime')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.baking_time_minutes ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, baking_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.ovenTemp')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.oven_temp_celsius ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, oven_temp_celsius: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.restTime')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.rest_time_minutes ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, rest_time_minutes: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid size={12}>
              <Alert severity="info" sx={infoAlertSx}>
                Touch = {t('productions:recipe.touchDescription')} | {t('productions:recipe.processDescription')}
              </Alert>
            </Grid>
            <Grid size={{ xs: 6, sm: 6 }}>
              <TextField
                label={t('productions:recipe.activeWorkMin')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.touch_minutes_standard ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, touch_minutes_standard: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0 }}
                helperText={t('productions:recipe.activeWorkHelper')}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 6 }}>
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
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.wastePct')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.waste_pct ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, waste_pct: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0, max: 100, step: 0.1 }}
                helperText="Perdida de materiales"
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label="% Depreciacion"
                type="number"
                size="small"
                fullWidth
                value={prodParams.overhead_pct ?? 5}
                onChange={(e) => onSetProdParams((p) => ({ ...p, overhead_pct: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 0, max: 100, step: 0.1 }}
                helperText="Amort. maquinaria (default 5%)"
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.traysPerBatch')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.trays_per_batch ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, trays_per_batch: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 1 }}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                label={t('productions:recipe.unitsPerTray')}
                type="number"
                size="small"
                fullWidth
                value={prodParams.units_per_tray ?? ''}
                onChange={(e) => onSetProdParams((p) => ({ ...p, units_per_tray: e.target.value ? Number(e.target.value) : null }))}
                inputProps={{ min: 1 }}
              />
            </Grid>
            <Grid size={12}>
              <TextField
                label={t('productions:recipe.instructions')}
                size="small"
                fullWidth
                multiline
                minRows={2}
                value={prodParams.instructions}
                onChange={(e) => onSetProdParams((p) => ({ ...p, instructions: e.target.value }))}
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
              <Chip label={`Prep: ${recipe.prep_time_minutes} min`} color="primary" size="small" />
            )}
            {recipe.baking_time_minutes != null && (
              <Chip label={`Horno: ${recipe.baking_time_minutes} min`} color="warning" size="small" />
            )}
            {recipe.oven_temp_celsius != null && (
              <Chip label={`${recipe.oven_temp_celsius} C`} color="default" size="small" />
            )}
            {recipe.rest_time_minutes != null && (
              <Chip label={`Reposo: ${recipe.rest_time_minutes} min`} color="info" size="small" />
            )}
            {(recipe as any).touch_minutes_standard != null && (recipe as any).touch_minutes_standard > 0 && (
              <Chip label={`Trabajo activo: ${(recipe as any).touch_minutes_standard} min`} color="success" size="small" />
            )}
            {(recipe as any).process_minutes != null && (recipe as any).process_minutes > 0 && (
              <Chip label={`Proceso: ${(recipe as any).process_minutes} min`} color="default" size="small" />
            )}
            {recipe.waste_pct != null && recipe.waste_pct > 0 && (
              <Chip label={`Merma: ${recipe.waste_pct}%`} color="error" size="small" />
            )}
            {recipe.overhead_pct != null && recipe.overhead_pct > 0 && (
              <Chip label={`Depreciacion: ${recipe.overhead_pct}%`} color="warning" size="small" />
            )}
            {recipe.trays_per_batch != null && (
              <Chip label={`${recipe.trays_per_batch} ${t('productions:recipe.traysLabel')}`} color="default" size="small" />
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
  )
}
