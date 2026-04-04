import React from 'react'
import {
  Box,
  Button,
  ButtonBase,
  Chip,
  IconButton,
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
import { Add, Delete } from '@mui/icons-material'
import type { Product } from '../../services/api/products'
import { convertQtyToUnit } from '../../services/unitService'
import { formatIngredientReference } from './ingredientCatalog'

type UnitOption = {
  code: string
  label: string
}

type IngredientDraft = {
  product_id: string
  qty: number
  unit: string
  package_unit: string
  qty_per_package: number
  package_cost: number
}

type Props = {
  t: (key: string, options?: any) => string
  isEditing: boolean
  ingredientsDraft: IngredientDraft[]
  products: Product[]
  units: UnitOption[]
  totalCost: number
  tableContainerSx: object
  onAddIngredient: () => void
  onSetIngredientField: (index: number, field: string, value: any) => void
  onRemoveIngredient: (index: number) => void
  onOpenIngredientInsight: (item: IngredientDraft, productName: string) => Promise<void> | void
}

export default function RecetaIngredientsTab({
  t,
  isEditing,
  ingredientsDraft,
  products,
  units,
  totalCost,
  tableContainerSx,
  onAddIngredient,
  onSetIngredientField,
  onRemoveIngredient,
  onOpenIngredientInsight,
}: Props) {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#334155' }}>
          Ingredientes de la receta
        </Typography>
        {isEditing && (
          <Button size="small" startIcon={<Add />} onClick={onAddIngredient} sx={{ borderRadius: 2.5, fontWeight: 600 }}>
            {t('productions:recipe.addIngredient')}
          </Button>
        )}
      </Box>
      <TableContainer component={Paper} variant="outlined" sx={tableContainerSx}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('productions:recipe.ingredients')}</TableCell>
              <TableCell align="right">{t('productions:recipe.quantity')}</TableCell>
              {isEditing && <TableCell>Unidad</TableCell>}
              <TableCell align="right">{t('productions:recipe.cost')}</TableCell>
              <TableCell align="right">%</TableCell>
              {isEditing && <TableCell />}
            </TableRow>
          </TableHead>
          <TableBody>
            {ingredientsDraft.length === 0 && (
              <TableRow>
                <TableCell colSpan={isEditing ? 6 : 4} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    {t('productions:recipe.noIngredients')}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {ingredientsDraft.map((item, index) => {
              const product = products.find((p) => p.id === item.product_id)
              const productName = product?.name || (item as any)?.product_name || '-'
              const qty = Number(item.qty ?? 0)
              const qtyReference = formatIngredientReference(qty, item.unit, units)
              const qtyInPackageUnit = convertQtyToUnit(
                Number(item.qty || 0),
                item.unit,
                item.package_unit || item.unit,
              )
              const estimatedCost =
                (qtyInPackageUnit / Math.max(Number(item.qty_per_package || 1), 0.0001)) *
                Number(item.package_cost || 0)
              const pct = totalCost > 0 ? (estimatedCost / totalCost) * 100 : 0
              return (
                <TableRow key={index}>
                  <TableCell>
                    {isEditing ? (
                      <TextField
                        select
                        SelectProps={{ native: true }}
                        value={item.product_id}
                        onChange={(e) => onSetIngredientField(index, 'product_id', e.target.value)}
                        size="small"
                        fullWidth
                      >
                        <option value="">{t('productions:recipe.selectProduct')}</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </TextField>
                    ) : (
                      <ButtonBase
                        onClick={() => void onOpenIngredientInsight(item, productName)}
                        sx={{
                          display: 'flex',
                          width: '100%',
                          alignItems: 'flex-start',
                          flexDirection: 'column',
                          textAlign: 'left',
                          borderRadius: 2,
                          px: 0.5,
                          py: 0.25,
                          '&:hover': {
                            backgroundColor: '#eff6ff',
                          },
                        }}
                      >
                        <Typography variant="body2" sx={{ fontWeight: 600, color: '#0f172a' }}>
                          {productName}
                        </Typography>
                        <Typography variant="caption" color="primary.main">
                          Ver ficha del ingrediente
                        </Typography>
                      </ButtonBase>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {isEditing ? (
                      <TextField
                        type="number"
                        value={item.qty}
                        onChange={(e) => onSetIngredientField(index, 'qty', Number(e.target.value))}
                        size="small"
                        sx={{ width: 90 }}
                      />
                    ) : (
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                        <Typography variant="body2">{`${qty.toFixed(2)} ${item.unit || ''}`.trim()}</Typography>
                        {qtyReference && (
                          <Typography variant="caption" color="text.secondary">
                            Equiv.: {qtyReference}
                          </Typography>
                        )}
                      </Box>
                    )}
                  </TableCell>
                  {isEditing && (
                    <TableCell>
                      <TextField
                        select
                        SelectProps={{ native: true }}
                        value={item.unit}
                        onChange={(e) => onSetIngredientField(index, 'unit', e.target.value)}
                        size="small"
                        sx={{ width: 90 }}
                      >
                        {units.map((unit) => (
                          <option key={unit.code} value={unit.code}>{unit.label}</option>
                        ))}
                      </TextField>
                    </TableCell>
                  )}
                  <TableCell align="right">
                    <strong>${estimatedCost.toFixed(2)}</strong>
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
                      <IconButton color="error" onClick={() => onRemoveIngredient(index)} size="small">
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
  )
}
