import React from 'react'
import {
  Alert,
  Box,
  Button,
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
import type { CostDriver } from '../../services/api/productionCosts'

type CostLineDraft = {
  id?: string
  driver_id: string
  qty_standard: number
  headcount: number
  rate_override: number | null
  notes?: string
  line_order?: number
  _isNew?: boolean
}

type ProdParams = {
  prep_time_minutes: number | null
  baking_time_minutes: number | null
  touch_minutes_standard: number | null
}

type Props = {
  t: (key: string, options?: any) => string
  isEditing: boolean
  costDrivers: CostDriver[]
  costLinesDraft: CostLineDraft[]
  prodParams: ProdParams
  infoAlertSx: object
  tableContainerSx: object
  normalizeCostDriverUnit: (unit?: string | null) => string
  isLaborAutoDriver: (driver?: CostDriver | null) => boolean
  onSetCostLinesDraft: React.Dispatch<React.SetStateAction<CostLineDraft[]>>
  onSetDeletedCostLineIds: React.Dispatch<React.SetStateAction<string[]>>
}

export default function RecetaCostsTab({
  t,
  isEditing,
  costDrivers,
  costLinesDraft,
  prodParams,
  infoAlertSx,
  tableContainerSx,
  normalizeCostDriverUnit,
  isLaborAutoDriver,
  onSetCostLinesDraft,
  onSetDeletedCostLineIds,
}: Props) {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#334155' }}>
          {t('productions:recipe.indirectCosts')}
        </Typography>
      </Box>

      {costDrivers.length === 0 && !isEditing && (
        <Alert severity="info" sx={{ ...infoAlertSx }}>
          {t('productions:recipe.noCostDriversInfo')}
        </Alert>
      )}

      {(costLinesDraft.length > 0 || isEditing) && (
        <TableContainer component={Paper} variant="outlined" sx={{ ...tableContainerSx, mb: isEditing ? 1.5 : 0 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('productions:recipe.costType')}</TableCell>
                <TableCell align="right">{t('productions:recipe.qty')}</TableCell>
                <TableCell align="right">{t('productions:recipe.headcount')}</TableCell>
                <TableCell align="right">{t('productions:recipe.rate')}</TableCell>
                <TableCell align="right">{t('productions:recipe.subtotal')}</TableCell>
                {isEditing && <TableCell />}
              </TableRow>
            </TableHead>
            <TableBody>
              {costLinesDraft.map((cl, idx) => {
                const driver = costDrivers.find((d) => d.id === cl.driver_id)
                const rate = cl.rate_override ?? (driver?.default_rate || 0)
                const driverUnitNorm = normalizeCostDriverUnit(driver?.unit)
                const isLaborAuto = isLaborAutoDriver(driver)
                const isEnergyDriver = !!driver && !isLaborAuto && (driver.consumption_rate ?? 0) > 0
                const isOvenAuto = isEnergyDriver
                const laborMinutes = prodParams.touch_minutes_standard ?? prodParams.prep_time_minutes ?? 0
                const recipeLaborHours = laborMinutes / 60
                const laborSource = prodParams.touch_minutes_standard != null
                  ? 'touch'
                  : (prodParams.prep_time_minutes != null ? 'prep' : null)
                const ovenMinutes = prodParams.baking_time_minutes ?? 0
                const ovenHours = ovenMinutes / 60
                const ovenAutoQty = isOvenAuto ? ovenHours * (driver!.consumption_rate ?? 0) : 0
                const effectiveQty = isLaborAuto && recipeLaborHours > 0
                  ? recipeLaborHours
                  : isOvenAuto && ovenMinutes > 0
                    ? ovenAutoQty
                    : Number(cl.qty_standard)
                const subtotal = effectiveQty * Number(rate) * (cl.headcount || 1)
                return (
                  <TableRow key={idx}>
                    <TableCell>
                      {isEditing ? (
                        <TextField
                          select
                          SelectProps={{ native: true }}
                          value={cl.driver_id}
                          onChange={(e) => {
                            onSetCostLinesDraft((prev) => {
                              const next = [...prev]
                              next[idx] = { ...next[idx], driver_id: e.target.value }
                              return next
                            })
                          }}
                          size="small"
                          fullWidth
                        >
                          <option value="">{t('productions:recipe.selectType')}</option>
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
                          <Typography variant="caption" color="text.secondary">
                            auto ({laborSource === 'touch' ? 'touch' : 'prep'} {laborMinutes} min)
                          </Typography>
                        </Box>
                      ) : isOvenAuto && ovenMinutes > 0 ? (
                        <Box>
                          <Typography variant="body2">{effectiveQty.toFixed(3)} {driverUnitNorm.includes('kw') ? 'kWh' : 'L'}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            auto (horno {ovenMinutes} min)
                          </Typography>
                        </Box>
                      ) : isEnergyDriver && !isOvenAuto ? (
                        <Box>
                          <Typography variant="body2" color="warning.main" sx={{ fontSize: '0.72rem' }}>Sin consumo/hr</Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>Configura en Costos Indirectos</Typography>
                        </Box>
                      ) : isEditing ? (
                        <TextField
                          type="number"
                          value={cl.qty_standard}
                          onChange={(e) => {
                            onSetCostLinesDraft((prev) => {
                              const next = [...prev]
                              next[idx] = { ...next[idx], qty_standard: Number(e.target.value) }
                              return next
                            })
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
                            onSetCostLinesDraft((prev) => {
                              const next = [...prev]
                              next[idx] = { ...next[idx], headcount: Number(e.target.value) || 1 }
                              return next
                            })
                          }}
                          size="small"
                          sx={{ width: 70 }}
                          inputProps={{ min: 1 }}
                        />
                      ) : (
                        cl.headcount
                      )}
                    </TableCell>
                    <TableCell align="right">${Number(rate).toFixed(2)}</TableCell>
                    <TableCell align="right"><strong>${subtotal.toFixed(2)}</strong></TableCell>
                    {isEditing && (
                      <TableCell align="right">
                        <IconButton
                          color="error"
                          size="small"
                          onClick={() => {
                            onSetCostLinesDraft((prev) => {
                              const target = prev[idx]
                              if (target?.id) {
                                onSetDeletedCostLineIds((ids) => [...ids, target.id!])
                              }
                              return prev.filter((_, i) => i !== idx)
                            })
                          }}
                        >
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
      )}

      {isEditing && (
        costDrivers.length > 0 ? (
          <Button
            size="small"
            startIcon={<Add />}
            onClick={() => {
              onSetCostLinesDraft((prev) => [
                ...prev,
                { driver_id: '', qty_standard: 1, headcount: 1, rate_override: null, line_order: prev.length, _isNew: true },
              ])
            }}
            sx={{ mt: 1 }}
          >
            {t('productions:recipe.addIndirectCost')}
          </Button>
        ) : (
          <Alert severity="warning" sx={{ borderRadius: 2.5, backgroundColor: '#fff7ed', border: '1px solid #fdba74', '& .MuiAlert-icon': { color: '#ea580c' } }}>
            {t('productions:recipe.noCostDrivers')}
          </Alert>
        )
      )}
    </Box>
  )
}
