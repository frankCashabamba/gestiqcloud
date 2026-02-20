import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import RecetaForm from './RecetaForm'
import { getRecipe, type Recipe } from '../../services/api/recetas'

export default function RecetaEditPage() {
  const nav = useNavigate()
  const { rid } = useParams()
  const [recipe, setRecipe] = useState<Recipe | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!rid) return
    ;(async () => {
      const r = await getRecipe(rid)
      if (!cancelled) setRecipe(r)
    })()
    return () => { cancelled = true }
  }, [rid])

  return (
    <RecetaForm open={true} recipe={recipe} onClose={() => nav('..', { replace: true })} />
  )
}
