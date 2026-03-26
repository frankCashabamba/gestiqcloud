import { describe, expect, it } from 'vitest'
import { buildIngredientMasterRows, formatIngredientReference } from './ingredientCatalog'

describe('ingredientCatalog', () => {
  it('groups ingredient references by product and marks divergent purchase data', () => {
    const rows = buildIngredientMasterRows(
      [
        {
          id: 'recipe-1',
          tenant_id: 'tenant',
          product_id: 'bread',
          name: 'Pan blanco',
          yield_qty: 40,
          total_cost: 0,
          unit_cost: 0,
          is_active: true,
          created_at: '',
          updated_at: '',
          ingredients: [
            {
              id: 'ing-1',
              recipe_id: 'recipe-1',
              product_id: 'harina',
              product_name: 'Harina',
              qty: 1000,
              unit: 'g',
              purchase_packaging: 'Saco 50 kg',
              qty_per_package: 50,
              package_unit: 'kg',
              package_cost: 25,
              ingredient_cost: 0,
              created_at: '',
            },
          ],
        },
        {
          id: 'recipe-2',
          tenant_id: 'tenant',
          product_id: 'cake',
          name: 'Queque',
          yield_qty: 10,
          total_cost: 0,
          unit_cost: 0,
          is_active: true,
          created_at: '',
          updated_at: '',
          ingredients: [
            {
              id: 'ing-2',
              recipe_id: 'recipe-2',
              product_id: 'harina',
              product_name: 'Harina',
              qty: 500,
              unit: 'g',
              purchase_packaging: 'Saco 45 kg',
              qty_per_package: 45,
              package_unit: 'kg',
              package_cost: 24,
              ingredient_cost: 0,
              created_at: '',
            },
          ],
        },
      ],
      [
        {
          id: 'harina',
          name: 'Harina',
          price: 0,
          tax_rate: 0,
          unit: 'kg',
        },
      ],
    )

    expect(rows).toHaveLength(1)
    expect(rows[0].product_id).toBe('harina')
    expect(rows[0].refs).toHaveLength(2)
    expect(rows[0].hasDivergence).toBe(true)
    expect(rows[0].inventory_product?.unit).toBe('kg')
  })

  it('formats weight references without duplicating the original unit column', () => {
    expect(formatIngredientReference(907, 'g')).toBe('0.907 kg / 2.000 lb')
    expect(formatIngredientReference(2, 'lb')).toBe('0.907 kg')
    expect(formatIngredientReference(5, 'uds')).toBeNull()
  })
})
