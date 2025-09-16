type Row = Record<string, string>

export function deduplicarPorInvoiceYFecha(rows: Row[], invoiceKey = 'invoice', fechaKey = 'fecha') {
  const seen = new Set<string>()
  const out: Row[] = []
  for (const r of rows) {
    const k = `${r[invoiceKey] || ''}::${r[fechaKey] || ''}`
    if (!seen.has(k)) { seen.add(k); out.push(r) }
  }
  return out
}

