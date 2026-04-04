import React, { Suspense, lazy } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'

const RecetaDetail = lazy(() => import('./RecetaDetail'))

export default function RecetaShowPage() {
  const nav = useNavigate()
  const { rid } = useParams()
  if (!rid) return null
  return (
    <ProductionAvailabilityGuard>
      <Suspense fallback={<div className="p-4">Loading recipe...</div>}>
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
      </Suspense>
    </ProductionAvailabilityGuard>
  )
}
