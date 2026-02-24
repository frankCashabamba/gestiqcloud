// Devuelve tipos alineados con backend: products | invoices | bank | expenses | recipes
export type ImportDocType = 'products' | 'invoices' | 'bank' | 'expenses' | 'recipes'

export function detectarTipoDocumento(headers: string[]): ImportDocType {
  const normalize = (s: string) =>
    (s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // quitar acentos
      .replace(/[^a-z0-9% ]+/g, ' ') // dejar alfanumérico básico y %
      .replace(/\s+/g, ' ') // colapsar espacios
      .trim()

  const H = headers.map(normalize)

  const hasAny = (keywords: string[]) =>
    H.some((h) => keywords.some((k) => h.includes(normalize(k))))

  const countHits = (keywords: string[]) =>
    H.reduce((n, h) => n + (keywords.some((k) => h.includes(normalize(k))) ? 1 : 0), 0)

  const recipeKeywords = ['ingredientes', 'receta', 'costo total ingredientes', 'porciones', 'temperatura de servicio', 'rendimiento']

  // --- Scoring por tipo ---
  const INVOICE_KW = ['factura', 'num factura', 'nro factura', 'invoice', 'cliente', 'ruc',
    'nif', 'vendedor', 'forma de pago', 'formas de pago', 'tipo identificacion',
    'numero identificacion', 'retencion', 'subtotal']
  const SALES_KW = ['venta', 'ventas', 'vendedor', 'cashier', 'cajero', 'ticket', 'recibo venta']
  const BANK_KW = ['iban', 'saldo', 'cuenta', 'concepto', 'valor', 'transaction', 'bank',
    'transferencia', 'banco', 'movimiento', 'debit', 'credit']
  const EXPENSES_KW = ['gasto', 'expense', 'receipt', 'recibo', 'nomina', 'salario']
  const PRODUCT_CATALOG_KW = ['sku', 'codigo', 'barcode', 'ean', 'upc', 'cod barras',
    'stock', 'existencias', 'inventario', 'categoria', 'familia']
  const NAME_FIELDS = ['producto', 'nombre', 'descripcion', 'articulo', 'item', 'detalle']
  const PRICE_FIELDS = ['precio', 'precio unitario', 'pvp', 'precio venta', 'importe', 'valor']

  if (hasAny(recipeKeywords)) return 'recipes'

  const invoiceScore = countHits(INVOICE_KW) + countHits(SALES_KW)
  const bankScore = countHits(BANK_KW)
  const expensesScore = countHits(EXPENSES_KW)
  const productScore = countHits(PRODUCT_CATALOG_KW)

  // Un reporte de ventas/facturas tiene campos de factura Y campos de producto (líneas).
  // La clave es que si hay "factura"/"cliente"/"vendedor" es un documento transaccional,
  // no un catálogo de productos.
  const hasStrongInvoiceSignal = hasAny(['factura', 'num factura', 'nro factura', 'invoice'])
  const hasStrongSalesSignal = hasAny(['vendedor', 'cashier', 'cajero', 'forma de pago', 'formas de pago'])

  // Si hay señales fuertes de factura/venta, priorizar sobre productos
  if (hasStrongInvoiceSignal || (invoiceScore >= 3 && hasStrongSalesSignal)) {
    return 'invoices'
  }

  if (bankScore >= 2 && bankScore > invoiceScore && bankScore > productScore) return 'bank'
  if (expensesScore >= 2 && expensesScore > invoiceScore) return 'expenses'

  // Solo clasificar como productos si parece un catálogo (sin señales de factura)
  const isProductCatalog =
    productScore >= 2 ||
    (hasAny(NAME_FIELDS) && (hasAny(PRICE_FIELDS) || hasAny(['stock', 'existencias'])))
  if (isProductCatalog && invoiceScore < 2) return 'products'

  if (invoiceScore >= 2) return 'invoices'
  if (productScore >= 1 && hasAny(NAME_FIELDS)) return 'products'

  return 'expenses'
}
