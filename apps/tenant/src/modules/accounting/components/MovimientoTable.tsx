import React, { useMemo } from 'react'
import type { Asiento } from '../types/movimiento'
import { MovimientoTipoBadge, type TipoMovimiento } from './MovimientoTipoBadge'
import { useTranslation } from 'react-i18next'

interface Props {
  asientos: Asiento[]
}

type Row = {
  id: string
  fecha: string
  cuenta: string
  categoria: string
  tipo: TipoMovimiento
  importe: number
}

export const MovimientoTable: React.FC<Props> = ({ asientos }) => {
  const { t } = useTranslation()
  const rows = useMemo<Row[]>(() => {
    const out: Row[] = []
    for (const a of asientos) {
      for (const ap of a.apuntes) {
        const isIngreso = ap.cuenta.startsWith('7') || (ap.haber ?? 0) > 0
        const isGasto = ap.cuenta.startsWith('6') || (ap.debe ?? 0) > 0
        const tipo: TipoMovimiento = isIngreso && !isGasto ? 'ingreso' : 'gasto'
        const importe = (ap.haber ?? 0) > 0 ? ap.haber : (ap.debe ?? 0)
        out.push({
          id: `${a.id}-${ap.cuenta}-${ap.description}`,
          fecha: a.fecha,
          cuenta: ap.cuenta,
          categoria: '-',
          tipo,
          importe,
        })
      }
    }
    return out
  }, [asientos])

  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 12, overflow: 'hidden', background: 'var(--color-surface)', margin: 16 }}>
      <table style={{ width: '100%', fontSize: 14 }}>
        <caption style={{ textAlign: 'left', padding: 8, color: 'var(--color-muted)' }}>{t('accounting.movimientos')}</caption>
        <thead style={{ background: 'var(--color-bg)' }}>
          <tr>
            <th scope="col" style={{ padding: 8, textAlign: 'left' }}>{t('common.date')}</th>
            <th scope="col" style={{ padding: 8, textAlign: 'left' }}>{t('common.account')}</th>
            <th scope="col" style={{ padding: 8, textAlign: 'left' }}>{t('common.category')}</th>
            <th scope="col" style={{ padding: 8, textAlign: 'center' }}>{t('common.type')}</th>
            <th scope="col" style={{ padding: 8, textAlign: 'right' }}>{t('common.amount')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.id} style={{ borderTop: '1px solid var(--color-border)' }}>
              <td style={{ padding: 8 }}>{m.fecha}</td>
              <td style={{ padding: 8 }}>{m.cuenta}</td>
              <td style={{ padding: 8 }}>{m.categoria}</td>
              <td style={{ padding: 8, textAlign: 'center' }}><MovimientoTipoBadge tipo={m.tipo} /></td>
              <td style={{ padding: 8, textAlign: 'right' }}>$ {m.importe.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
