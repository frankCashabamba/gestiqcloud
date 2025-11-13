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

// Normaliza filas de Excel a productos con detección por secciones.
// - Si no existe columna 'categoria', detecta filas encabezado (solo texto, sin precio/stock)
//   y propaga esa categoría a las filas siguientes hasta el próximo encabezado.
// - NO fuerza categoría por defecto si falta.
export function normalizarProductos(rows: Row[]): Record<string, unknown>[] {
  if (!rows || rows.length === 0) return []
  const headers = Object.keys(rows[0] || {})

  const colCodigo = findCol(headers, ['sku', 'codigo', 'cod', 'referencia', 'ref', 'barcode', 'ean', 'upc', 'codigo barras', 'cod barras'])
  const colNombre = findCol(headers, ['producto', 'prodcuto', 'nombre', 'descripcion', 'articulo', 'item', 'detalle'])
  const colPrecio = findCol(headers, ['precio unitario venta', 'precio', 'pvp', 'precio venta', 'importe', 'valor'])
  const colStock  = findCol(headers, ['cantidad', 'stock', 'existencias', 'qty', 'unidades', 'inventario'])
  const colCategoria = findCol(headers, ['categoria', 'familia', 'rubro', 'grupo', 'subcategoria'])

  let currentCategory = ''
  const out: Record<string, unknown>[] = []

  const looksLikeHeader = (text: string): boolean => {
    const t = (text || '').trim()
    if (!t) return false
    const upperRatio = t.replace(/[^A-Z]/g, '').length / t.length
    const hasDigits = /\d/.test(t)
    const tokens = t.split(/\s+/)
    const banned = /^(total|subtotal|observaciones|nota|otros|varios)$/i
    if (banned.test(t)) return false
    // Header heuristics: mostly uppercase, few tokens, no digits
    return upperRatio >= 0.6 && tokens.length <= 4 && !hasDigits
  }

  for (const r of rows) {
    const precioVal = toNumber(colPrecio ? r[colPrecio] : undefined)
    const stockVal  = toNumber(colStock ? r[colStock] : undefined)
    const nombreVal = (colNombre ? r[colNombre] : r['nombre']) || ''
    const codigoVal = (colCodigo ? r[colCodigo] : r['codigo']) || ''

    const nonEmptyCount = Object.values(r).filter((v) => String(v ?? '').trim() !== '').length
    const hasCategoryCol = !!colCategoria

    if (!hasCategoryCol) {
      const headerText = String(colNombre ? r[colNombre] : Object.values(r)[0] || '').trim()
      const isHeader = headerText && !precioVal && !stockVal && nonEmptyCount <= 2 && looksLikeHeader(headerText)
      if (isHeader) {
        currentCategory = headerText
        continue
      }
    }

    const categoriaRaw = colCategoria ? r[colCategoria] : undefined
    const categoria = categoriaRaw ? String(categoriaRaw).trim() : currentCategory

    // ignorar filas de totales/observaciones comunes
    const firstCell = String(Object.values(r)[0] ?? '').trim()
    if (/^(total|subtotal|observaciones|nota)$/i.test(firstCell)) continue

    // saltar filas vacías
    if (!nombreVal && !precioVal && !stockVal && !codigoVal) continue

    out.push({
      codigo: codigoVal || undefined,
      nombre: nombreVal,
      precio: precioVal,
      stock: stockVal,
      categoria: categoria || '',
      pvp: precioVal || undefined,
      cantidad: stockVal || undefined,
      unidad: 'unit',
    })
  }

  return out
}
