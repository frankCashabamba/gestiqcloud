/**
 * normalizeOCRFields.ts
 * Normaliza campos extraídos por OCR al schema canónico del backend.
 *
 * Problema: El OCR extrae campos en español (fecha, importe, concepto)
 * pero la validación espera campos canónicos (transaction_date, amount, description)
 */

type Row = Record<string, unknown>

/**
 * Mapeo de campos OCR español → schema canónico
 */
const OCR_FIELD_MAPPINGS: Record<string, Record<string, string>> = {
  // Banco / Transferencias
  bank: {
    fecha: 'value_date',
    importe: 'amount',
    monto: 'amount',
    concepto: 'narrative',
    descripcion: 'narrative',
    cuenta: 'counterparty',
    origen: 'source',
    tipo: 'direction',
    saldo: 'balance',
    referencia: 'external_ref',
  },
  // Gastos
  expenses: {
    fecha: 'expense_date',
    importe: 'amount',
    monto: 'amount',
    concepto: 'description',
    descripcion: 'description',
    categoria: 'category',
    proveedor: 'vendor_name',
    metodo_pago: 'payment_method',
    tipo: 'category',
  },
  // Facturas
  invoices: {
    // Backend validator for source_type=invoices expects: invoice_number + invoice_date (+ total_amount optional)
    // Map legacy OCR fields to those keys.
    fecha: 'invoice_date',
    issue_date: 'invoice_date',
    importe: 'total_amount',
    monto: 'total_amount',
    total: 'total_amount',
    subtotal: 'net_amount',
    iva: 'tax_amount',
    concepto: 'concept',
    descripcion: 'concept',
    proveedor: 'vendor_name',
    // For supplier invoices, "cliente" in legacy OCR payload usually refers to the vendor/supplier.
    cliente: 'vendor_name',
    numero_factura: 'invoice_number',
    factura: 'invoice_number',
    invoice: 'invoice_number',
  },
  // Productos (generalmente no viene de OCR, pero por si acaso)
  products: {
    nombre: 'name',
    precio: 'price',
    cantidad: 'stock',
    categoria: 'category',
    descripcion: 'description',
  },
}

/**
 * Normaliza un row OCR al schema canónico según el tipo de documento
 */
function toStringValue(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return ''
}

export function normalizeOCRRow(row: Row, docType: string): Row {
  const today = new Date().toISOString().slice(0, 10)
  // Canonical schema from backend OCR (doc_type/totals/lines/issue_date...)
  const canonicalType = toStringValue(row.doc_type).toLowerCase()
  if (canonicalType || row.totals || row.lines || row.issue_date || row.invoice_number) {
    const totals = (row.totals as Record<string, unknown>) || {}
    const lines = Array.isArray(row.lines) ? (row.lines as Array<Record<string, unknown>>) : []
    const firstLine = lines[0] || {}
    const routing = (row.routing_proposal as Record<string, unknown>) || {}

    // Invoice canonical -> legacy invoices ingest fields expected by backend validator
    if (docType === 'invoices' || canonicalType === 'invoice') {
      const vendor = (row.vendor as Record<string, unknown>) || {}
      const taxBreakdown = Array.isArray((totals as any).tax_breakdown) ? ((totals as any).tax_breakdown as any[]) : []
      const taxRate = taxBreakdown.length ? toStringValue(taxBreakdown[0]?.rate) : ''
      return {
        // Required by validate_invoices()
        invoice_number: toStringValue(row.invoice_number ?? row.invoice ?? ''),
        invoice_date: toStringValue(row.issue_date ?? row.invoice_date ?? row.fecha ?? '') || today,
        total_amount: toStringValue((totals as any).total ?? row.total ?? ''),
        net_amount: toStringValue((totals as any).subtotal ?? (totals as any).net ?? ''),
        tax_amount: toStringValue((totals as any).tax ?? ''),
        tax_rate: taxRate,
        currency: toStringValue(row.currency ?? ''),
        // Helpful metadata (not required)
        issuer: toStringValue((vendor as any).name ?? ''),
        issuer_tax_id: toStringValue((vendor as any).tax_id ?? ''),
        country: toStringValue(row.country ?? ''),
        description:
          toStringValue(row.description ?? row.concept ?? firstLine.desc ?? '') ||
          toStringValue(row.doc_type || row.documentoTipo || 'Factura OCR'),
        vendor_name: toStringValue((vendor as any).name ?? ''),
        category: toStringValue(row.category ?? row.categoria ?? (routing as any).category_code ?? ''),
        // Keep original structures for later steps (backend can ignore unknown keys)
        totals,
        lines,
        documentoTipo: toStringValue(row.doc_type ?? row.documentoTipo ?? row.tipo ?? 'invoice'),
        origen: toStringValue(row.source ?? row.origen ?? 'ocr'),
      }
    }

    const amount =
      row.amount
      ?? row.total
      ?? totals.total
      ?? firstLine.total
      ?? firstLine.unit_price
      ?? ''
    const description =
      row.description
      ?? row.concept
      ?? firstLine.desc
      ?? toStringValue(row.doc_type || row.documentoTipo || 'Documento OCR')

    return {
      expense_date: toStringValue(row.expense_date ?? row.issue_date ?? row.invoice_date ?? row.fecha ?? '') || today,
      amount: toStringValue(amount),
      description: toStringValue(description),
      category: toStringValue(row.category ?? row.categoria ?? routing.category_code ?? ''),
      cliente: toStringValue((row.buyer as Record<string, unknown>)?.name ?? row.cliente ?? ''),
      invoice: toStringValue(row.invoice_number ?? row.invoice ?? ''),
      cuenta: toStringValue(routing.account ?? row.cuenta ?? ''),
      origen: toStringValue(row.source ?? row.origen ?? 'ocr'),
      documentoTipo: toStringValue(row.doc_type ?? row.documentoTipo ?? row.tipo ?? ''),
    }
  }

  const mappings = OCR_FIELD_MAPPINGS[docType] || {}
  const normalized: Row = {}

  for (const [key, value] of Object.entries(row)) {
    const normalizedKey = mappings[key.toLowerCase()] || key
    normalized[normalizedKey] = toStringValue(value)
  }

  // Añadir campos faltantes con defaults
  if (docType === 'bank' && normalized.amount && !normalized.direction) {
    // Inferir dirección desde el signo del importe
    const amount = parseFloat(toStringValue(normalized.amount).replace(',', '.'))
    if (!isNaN(amount)) {
      normalized.direction = amount < 0 ? 'debit' : 'credit'
      normalized.amount = String(Math.abs(amount))
    }
  }

  if (docType === 'expenses' && !toStringValue(normalized.expense_date)) {
    normalized.expense_date = today
  }

  // For invoices: don't default dates; but if we got issue_date mapped, ensure invoice_date exists.
  if (docType === 'invoices') {
    const invDate = toStringValue((normalized as any).invoice_date)
    const issueDate = toStringValue((normalized as any).issue_date)
    if (!invDate && issueDate) {
      ;(normalized as any).invoice_date = issueDate
    }
    // If total_amount missing but we have total, copy it (legacy).
    const totalAmount = toStringValue((normalized as any).total_amount)
    const total = toStringValue((normalized as any).total)
    if (!totalAmount && total) {
      ;(normalized as any).total_amount = total
    }
  }

  return normalized
}

/**
 * Normaliza múltiples rows
 */
export function normalizeOCRRows(rows: Row[], docType: string): Row[] {
  return rows.map(row => normalizeOCRRow(row, docType))
}

/**
 * Detecta el tipo de documento basándose en los campos presentes
 */
export function inferDocTypeFromFields(headers: string[]): string {
  const headersLower = headers.map(h => h.toLowerCase())

  // Banco
  const bankFields = ['iban', 'cuenta', 'saldo', 'balance', 'transferencia']
  if (bankFields.some(f => headersLower.some(h => h.includes(f)))) {
    return 'bank'
  }

  // Facturas
  const invoiceFields = ['factura', 'invoice', 'ruc', 'cif', 'iva', 'nif']
  if (invoiceFields.some(f => headersLower.some(h => h.includes(f)))) {
    return 'invoices'
  }

  // Productos
  const productFields = ['producto', 'sku', 'stock', 'precio', 'price']
  if (productFields.some(f => headersLower.some(h => h.includes(f)))) {
    return 'products'
  }

  // Default a gastos para OCR genérico
  return 'expenses'
}

export default {
  normalizeOCRRow,
  normalizeOCRRows,
  inferDocTypeFromFields,
}
