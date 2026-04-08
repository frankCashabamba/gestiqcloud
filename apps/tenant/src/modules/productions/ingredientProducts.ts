import type { Product } from '../../services/api/products'

export function mergeIngredientProducts(
  rawMaterials: Product[],
  fallbackProducts: Product[] = [],
  preferredIds: Iterable<string> = [],
): Product[] {
  const preferred = new Set<string>()
  for (const id of preferredIds) {
    const normalized = String(id || '').trim()
    if (normalized) preferred.add(normalized)
  }

  const byId = new Map<string, Product>()

  const addProducts = (items: Product[], onlyPreferred = false) => {
    for (const product of items) {
      const id = String(product?.id || '').trim()
      if (!id || byId.has(id)) continue
      if (onlyPreferred && preferred.size === 0) continue
      if (onlyPreferred && preferred.size > 0 && !preferred.has(id)) continue
      byId.set(id, product)
    }
  }

  addProducts(rawMaterials)
  addProducts(fallbackProducts, true)

  return [...byId.values()].sort((left, right) => left.name.localeCompare(right.name))
}
