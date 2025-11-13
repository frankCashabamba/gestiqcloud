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
      onCreateOrder={(recipe) => nav(`../ordenes/nuevo?recipeId=${encodeURIComponent(recipe.id)}&productId=${encodeURIComponent(recipe.product_id)}`)}
    />
  )
}
