import React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import RecetaDetail from './RecetaDetail'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'

export default function RecetaShowPage() {
  const nav = useNavigate()
  const { rid } = useParams()
  if (!rid) return null
  return (
    <ProductionAvailabilityGuard>
      <RecetaDetail
        open={true}
        recipeId={rid}
        onClose={() => nav('..', { replace: true })}
        onCreateOrder={(recipe, options) => {
          const params = new URLSearchParams({
            recipeId: String(recipe.id),
            productId: String(recipe.product_id),
          })
          if (options?.qty && options.qty > 0) params.set('qty', String(options.qty))
          if (options?.autoCreate) params.set('autoCreate', '1')
          nav(`../ordenes/nuevo?${params.toString()}`)
        }}
      />
    </ProductionAvailabilityGuard>
  )
}
