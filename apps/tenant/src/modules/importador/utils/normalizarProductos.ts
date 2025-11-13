type Row = Record<string, string>

const norm = (s: string) =>
  (s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9% ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

function findCol(headers: string[], keywords: string[]): string | undefined {
  const H = headers.map(norm)
  for (const k of keywords.map(norm)) {
    const idx = H.findIndex((h) => h.includes(k))
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
 * Normaliza filas genéricas de Excel a un shape de productos.
 * Intenta detectar columnas: codigo, nombre, precio, stock, categoria.
 * Si falta categoria, usa 'pan' por defecto para panaderías.
 */
export function normalizarProductos(rows: Row[]): Record<string, unknown>[] {
  if (!rows || rows.length === 0) return []
  const headers = Object.keys(rows[0] || {})

  const colCodigo = findCol(headers, ['sku', 'codigo', 'cod', 'referencia', 'ref', 'barcode', 'ean', 'upc', 'codigo barras', 'cod barras'])
  const colNombre = findCol(headers, ['producto','prodcuto','nombre','descripcion','articulo','item','detalle'])
  const colPrecio = findCol(headers, ['precio unitario venta', 'precio', 'pvp', 'precio venta', 'importe', 'valor'])
  const colStock = findCol(headers, ['cantidad', 'stock', 'existencias', 'qty', 'unidades', 'inventario'])
  const colCategoria = findCol(headers, ['categoria','familia','rubro','grupo','subcategoria'])

  return rows.map((r) => {
    const precio = toNumber(colPrecio ? r[colPrecio] : undefined)
    const stock = toNumber(colStock ? r[colStock] : undefined)
    const nombre = (colNombre ? r[colNombre] : r['nombre']) || ''
    const codigo = (colCodigo ? r[colCodigo] : r['codigo']) || ''
    const categoria = colCategoria ? String(r[colCategoria]).trim() : ''

    return {
      codigo: codigo || undefined,
      nombre,
      precio,
      stock,
      categoria,
      // Campos opcionales útiles si existen
      pvp: precio || undefined,
      cantidad: stock || undefined,
      unidad: 'unit',
    }
  })
}

