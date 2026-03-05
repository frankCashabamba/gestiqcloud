type Row = Record<string, string>
type Mapa = Partial<Record<'fecha'|'concepto'|'monto', string>>

const normalizeKey = (s: string) =>
  (s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

const toNum = (value: unknown): number => {
  const raw = String(value ?? '').trim()
  if (!raw) return 0
  return Number(raw.replace(/[^0-9.,-]/g, '').replace(',', '.')) || 0
}

const pick = (row: Row, candidates: string[]): string => {
  const idx: Record<string, string> = {}
  for (const [k, v] of Object.entries(row)) idx[normalizeKey(k)] = String(v ?? '')
  for (const c of candidates) {
    const v = idx[normalizeKey(c)]
    if (typeof v === 'string' && v.trim()) return v
  }
  return ''
}

export function normalizarDocumento(rows: Row[], mapa: Mapa, docType: string = 'expenses') {
  const kind = (docType || 'expenses').toLowerCase()

  const normalized = rows.map((r) => {
    const fecha = (mapa.fecha ? r[mapa.fecha] : '') || pick(r, ['fecha', 'date', 'invoice_date', 'issue_date', 'expense_date'])
    const concepto = (mapa.concepto ? r[mapa.concepto] : '') || pick(r, ['concepto', 'descripcion', 'description', 'detalle', 'narrative'])
    const montoRaw = (mapa.monto ? r[mapa.monto] : '') || pick(r, ['monto', 'importe', 'total', 'amount', 'valor'])
    const monto = toNum(montoRaw)

    if (kind === 'invoices' || kind === 'invoice' || kind === 'sales_invoice' || kind === 'purchase_invoice') {
      const invoiceNumber = pick(r, [
        'invoice_number',
        'nro_factura',
        'numero_factura',
        'no_factura',
        'num_factura',
        'n_factura',
        'factura',
        'invoice',
        'documento',
        'numero_documento',
      ])
      return {
        invoice_number: invoiceNumber,
        invoice_date: fecha,
        total_amount: monto,
        concept: concepto,
      }
    }

    if (kind === 'bank' || kind === 'bank_transactions' || kind === 'bank_tx') {
      return {
        transaction_date: fecha,
        amount: monto,
        description: concepto,
      }
    }

    return {
      expense_date: fecha,
      description: concepto,
      amount: monto,
    }
  })

  if (kind === 'invoices' || kind === 'invoice' || kind === 'sales_invoice' || kind === 'purchase_invoice') {
    return normalized.filter((d: any) =>
      String(d.invoice_number || '').trim() ||
      String(d.invoice_date || '').trim() ||
      Number(d.total_amount || 0) !== 0 ||
      String(d.concept || '').trim()
    )
  }

  if (kind === 'bank' || kind === 'bank_transactions' || kind === 'bank_tx') {
    return normalized.filter((d: any) =>
      String(d.transaction_date || '').trim() ||
      Number(d.amount || 0) !== 0 ||
      String(d.description || '').trim()
    )
  }

  return normalized.filter((d: any) =>
    String(d.expense_date || '').trim() ||
    Number(d.amount || 0) !== 0 ||
    String(d.description || '').trim()
  )
}
