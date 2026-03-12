import React from 'react'
import { useNavigate } from 'react-router-dom'
import RecetaForm from './RecetaForm'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'

export default function RecetaCreatePage() {
  const nav = useNavigate()
  return (
    <ProductionAvailabilityGuard>
      <RecetaForm open={true} recipe={null} onClose={() => nav('..', { replace: true })} />
    </ProductionAvailabilityGuard>
  )
}
