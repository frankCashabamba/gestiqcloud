export interface RestaurantMenuProduct {
  id: string
  name: string
  price: number
  active?: boolean
  is_raw_material?: boolean
}

export function filterRestaurantMenuProducts(products: RestaurantMenuProduct[]) {
  return products.filter((product) =>
    product.active !== false &&
    product.is_raw_material !== true &&
    Number(product.price ?? 0) >= 0
  )
}
