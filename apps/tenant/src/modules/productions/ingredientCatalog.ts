import type { Recipe } from '../../services/api/recetas'
import type { Product } from '../../services/api/products'

type UnitLike = {
  code: string
  label: string
}

const MASS_UNIT_ALIASES: Record<string, string> = {
  g: 'g',
  gr: 'g',
  gramo: 'g',
  gramos: 'g',
  kg: 'kg',
  kilo: 'kg',
  kilos: 'kg',
  kilogramo: 'kg',
  kilogramos: 'kg',
  lb: 'lb',
  lbs: 'lb',
  libra: 'lb',
  libras: 'lb',
  oz: 'oz',
  onza: 'oz',
  onzas: 'oz',
}

function normalizeMeasureUnit(value: string | null | undefined): string {
  const normalized = String(value || '').trim().toLowerCase()
  return MASS_UNIT_ALIASES[normalized] || normalized
}

export interface IngredientRef {
  recipe_id: string
  ingredient_id: string
  recipe_name: string
  qty: number
  unit: string
}

export interface IngredientMasterRow {
  product_id: string
  product_name: string
  inventory_product?: Product
  unit: string
  purchase_packaging: string
  qty_per_package: number
  package_unit: string
  package_cost: number
  refs: IngredientRef[]
  hasDivergence: boolean
}

export function buildIngredientMasterRows(
  recipes: Recipe[],
  products: Product[],
): IngredientMasterRow[] {
  const productMap = new Map<string, Product>()
  for (const product of products) {
    productMap.set(product.id, product)
  }

  const map = new Map<string, IngredientMasterRow>()

  for (const recipe of recipes) {
    for (const ingredient of recipe.ingredients || []) {
      const productId = String(ingredient.product_id || '').trim()
      if (!productId) continue

      const inventoryProduct = productMap.get(productId)
      const productName =
        String(ingredient.product_name || '').trim() ||
        String(inventoryProduct?.name || '').trim() ||
        productId

      const nextValues = {
        purchase_packaging: String(ingredient.purchase_packaging ?? ''),
        qty_per_package: Number(ingredient.qty_per_package ?? 1),
        package_unit: String(ingredient.package_unit ?? ingredient.unit ?? ''),
        package_cost: Number(ingredient.package_cost ?? 0),
      }

      if (!map.has(productId)) {
        map.set(productId, {
          product_id: productId,
          product_name: productName,
          inventory_product: inventoryProduct,
          unit: String(ingredient.unit ?? inventoryProduct?.unit ?? ''),
          ...nextValues,
          refs: [],
          hasDivergence: false,
        })
      }

      const current = map.get(productId)!
      if (
        current.purchase_packaging !== nextValues.purchase_packaging ||
        current.qty_per_package !== nextValues.qty_per_package ||
        current.package_unit !== nextValues.package_unit ||
        current.package_cost !== nextValues.package_cost
      ) {
        current.hasDivergence = true
      }

      current.refs.push({
        recipe_id: String(recipe.id),
        ingredient_id: String((ingredient as { id?: string }).id ?? ''),
        recipe_name: String(recipe.name ?? ''),
        qty: Number(ingredient.qty ?? 0),
        unit: String(ingredient.unit ?? ''),
      })
    }
  }

  return [...map.values()].sort((left, right) =>
    left.product_name.localeCompare(right.product_name),
  )
}

export async function fetchIngredientMasterRows(): Promise<IngredientMasterRow[]> {
  const [{ listRecipes }, { listProducts }] = await Promise.all([
    import('../../services/api/recetas'),
    import('../../services/api/products'),
  ])
  const [recipes, products] = await Promise.all([
    listRecipes({ limit: 500, include_ingredients: true }),
    listProducts({ limit: 500 }),
  ])

  return buildIngredientMasterRows(
    Array.isArray(recipes) ? recipes : [],
    Array.isArray(products) ? products : [],
  )
}

export function formatIngredientReference(
  qty: number,
  unit: string | null | undefined,
  _units: UnitLike[] = [],
): string | null {
  const normalizedUnit = normalizeMeasureUnit(unit)

  if (normalizedUnit === 'g') {
    return `${(qty / 1000).toFixed(3)} kg / ${(qty / 453.592).toFixed(3)} lb`
  }
  if (normalizedUnit === 'kg') {
    return `${(qty * 2.20462).toFixed(3)} lb`
  }
  if (normalizedUnit === 'lb') {
    return `${(qty / 2.20462).toFixed(3)} kg`
  }
  if (normalizedUnit === 'oz') {
    const pounds = qty / 16
    return `${(pounds / 2.20462).toFixed(3)} kg / ${pounds.toFixed(3)} lb`
  }

  return null
}
