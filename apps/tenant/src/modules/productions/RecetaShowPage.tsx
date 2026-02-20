import React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import RecetaDetail from './RecetaDetail'

export default function RecetaShowPage() {
  const nav = useNavigate()
  const { rid } = useParams()
  if (!rid) return null
  return (
    <RecetaDetail
      open={true}
      recipeId={rid}
      onClose={() => nav('..', { replace: true })}
      onEdit={(recipe) => nav(`../${encodeURIComponent(recipe.id)}/editar`)}
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
  )
}
