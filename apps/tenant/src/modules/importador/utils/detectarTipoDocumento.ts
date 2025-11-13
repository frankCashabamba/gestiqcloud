// Mejora: detección robusta para "productos" considerando sinónimos y acentos
export function detectarTipoDocumento(headers: string[]): 'generico' | 'factura' | 'recibo' | 'transferencia' | 'productos' {
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

  // Sinónimos por campo
  const NAME_FIELDS = ['producto', 'nombre', 'descripcion', 'articulo', 'item', 'detalle']
  const SKU_FIELDS = ['sku', 'codigo', 'cod', 'referencia', 'ref', 'barcode', 'ean', 'upc', 'cod barras', 'codigo barras']
  const PRICE_FIELDS = ['precio', 'precio unitario', 'pvp', 'precio venta', 'importe', 'valor']
  const COST_FIELDS = ['costo', 'coste', 'precio costo']
  const STOCK_FIELDS = ['stock', 'existencias', 'cantidad', 'qty', 'unidades', 'inventario']
  const CATEGORY_FIELDS = ['categoria', 'familia', 'rubro', 'grupo', 'subcategoria']
  const TAX_FIELDS = ['iva', 'impuesto', 'tax', 'tasa', 'tipo iva']

  // Regla principal: es productos si hay SKU o (Nombre/Descripción y Precio/Stock/Coste)
  const isProductos =
    hasAny(SKU_FIELDS) ||
    (hasAny(NAME_FIELDS) && (hasAny(PRICE_FIELDS) || hasAny(STOCK_FIELDS) || hasAny(COST_FIELDS))) ||
    // Heurística adicional: presencia combinada de categoría o impuestos junto a nombre
    (hasAny(NAME_FIELDS) && (hasAny(CATEGORY_FIELDS) || hasAny(TAX_FIELDS)))

  if (isProductos) return 'productos'

  // Otros tipos (básicos)
  if (hasAny(['invoice', 'nro factura', 'factura', 'cliente', 'nif', 'ruc'])) return 'factura'
  if (hasAny(['recibo', 'empleado'])) return 'recibo'
  if (hasAny(['banco', 'iban', 'transferencia'])) return 'transferencia'
  return 'generico'
}
