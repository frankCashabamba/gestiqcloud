type Row = Record<string, string>

const normalize = (s: string) =>
  (s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9% ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

function findColumn(headers: string[], keywords: string[]): string | undefined {
  const normalizedHeaders = headers.map(normalize)
  for (const k of keywords.map(normalize)) {
    const idx = normalizedHeaders.findIndex((h) => h.includes(k))
    if (idx !== -1) return headers[idx]
  }
  return undefined
}

function toNumber(v: unknown): number {
  if (v == null) return 0
  const s = String(v)
  const num = Number(s.replace(/[^0-9.,-]/g, '').replace(',', '.'))
  return Number.isFinite(num) ? num : 0
}

/**
 * Normalizes generic Excel rows to a product shape.
 * Attempts to detect columns: code, name, price, stock, category.
 * If category is missing, defaults to 'bread' for bakeries.
 */
export function normalizeProducts(rows: Row[]): Record<string, unknown>[] {
  if (!rows || rows.length === 0) return []
  const headers = Object.keys(rows[0] || {})

  const codeColumn = findColumn(headers, ['sku', 'codigo', 'cod', 'referencia', 'ref', 'barcode', 'ean', 'upc', 'codigo barras', 'cod barras'])
  const nameColumn = findColumn(headers, ['producto', 'prodcuto', 'nombre', 'descripcion', 'articulo', 'item', 'detalle'])
  const priceColumn = findColumn(headers, ['precio unitario venta', 'precio', 'pvp', 'precio venta', 'importe', 'valor'])
  const stockColumn = findColumn(headers, ['cantidad', 'stock', 'existencias', 'qty', 'unidades', 'inventario'])
  const categoryColumn = findColumn(headers, ['categoria', 'familia', 'rubro', 'grupo', 'subcategoria'])

  return rows.map((r) => {
    const price = toNumber(priceColumn ? r[priceColumn] : undefined)
    const stock = toNumber(stockColumn ? r[stockColumn] : undefined)
    const name = (nameColumn ? r[nameColumn] : r['nombre']) || ''
    const code = (codeColumn ? r[codeColumn] : r['codigo']) || ''
    const category = categoryColumn ? String(r[categoryColumn]).trim() : ''

    return {
      code: code || undefined,
      name,
      price,
      stock,
      category,
      // Useful optional fields if they exist
      pvp: price || undefined,
      quantity: stock || undefined,
      unit: 'unit',
    }
  })
}
