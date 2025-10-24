/**
 * Product Grid - Grid de productos con cards touch-optimized
 */
import React from 'react'
import ProductCard from './ProductCard'

type Product = {
  id: string
  name: string
  sku?: string
  price: number
  image_url?: string
  stock?: number
  category?: string
}

type ProductGridProps = {
  products: Product[]
  onProductClick: (product: Product) => void
}

export default function ProductGrid({ products, onProductClick }: ProductGridProps) {
  if (products.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <svg className="mx-auto h-16 w-16 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="mt-4 text-lg font-medium text-slate-600">No hay productos disponibles</p>
          <p className="mt-1 text-sm text-slate-500">Importa productos desde el backoffice</p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          onClick={() => onProductClick(product)}
        />
      ))}
    </div>
  )
}
