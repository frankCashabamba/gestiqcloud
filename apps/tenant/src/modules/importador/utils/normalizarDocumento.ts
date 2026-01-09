type Row = Record<string, string | number>
type Mapa = Partial<Record<'fecha'|'concepto'|'monto', string>>

export function normalizarDocumento(rows: Row[], mapa: Mapa) {
  return rows.map((r) => {
    const fecha = (mapa.fecha ? r[mapa.fecha] : r['fecha']) || ''
    const concepto = (mapa.concepto ? r[mapa.concepto] : r['concepto']) || ''
    const montoRaw = (mapa.monto ? r[mapa.monto] : r['monto']) || '0'
    const monto = Number(String(montoRaw).replace(/[^0-9.,-]/g, '').replace(',', '.')) || 0
    return { fecha, concepto, monto }
  })
}
