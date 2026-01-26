/**
 * normalizeOCRFields.ts
 * Normaliza campos extraídos por OCR al schema canónico del backend.
 * 
 * Problema: El OCR extrae campos en español (fecha, importe, concepto)
 * pero la validación espera campos canónicos (transaction_date, amount, description)
 */

type Row = Record<string, string>

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
    fecha: 'issue_date',
    importe: 'total',
    monto: 'total',
    total: 'total',
    subtotal: 'subtotal',
    iva: 'tax',
    concepto: 'concept',
    descripcion: 'concept',
    proveedor: 'vendor_name',
    cliente: 'customer_name',
    numero_factura: 'invoice_number',
    factura: 'invoice_number',
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
export function normalizeOCRRow(row: Row, docType: string): Row {
  const mappings = OCR_FIELD_MAPPINGS[docType] || {}
  const normalized: Row = {}

  for (const [key, value] of Object.entries(row)) {
    const normalizedKey = mappings[key.toLowerCase()] || key
    normalized[normalizedKey] = value
  }

  // Añadir campos faltantes con defaults
  if (docType === 'bank' && normalized.amount && !normalized.direction) {
    // Inferir dirección desde el signo del importe
    const amount = parseFloat(normalized.amount.replace(',', '.'))
    if (!isNaN(amount)) {
      normalized.direction = amount < 0 ? 'debit' : 'credit'
      normalized.amount = String(Math.abs(amount))
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
