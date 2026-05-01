import { describe, expect, it } from 'vitest'
import { filterRestaurantMenuProducts } from './menuProducts'

describe('filterRestaurantMenuProducts', () => {
  it('keeps active sellable products and excludes raw materials', () => {
    const products = filterRestaurantMenuProducts([
      { id: 'bread', name: 'Pan', price: 1.2, active: true, is_raw_material: false },
      { id: 'flour', name: 'Harina', price: 0.5, active: true, is_raw_material: true },
      { id: 'old-menu', name: 'Menu antiguo', price: 8, active: false, is_raw_material: false },
    ])

    expect(products.map((product) => product.id)).toEqual(['bread'])
  })
})
