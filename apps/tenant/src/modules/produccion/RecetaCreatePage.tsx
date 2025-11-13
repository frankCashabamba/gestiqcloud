import React from 'react'
import { useNavigate } from 'react-router-dom'
import RecetaForm from './RecetaForm'

export default function RecetaCreatePage() {
  const nav = useNavigate()
  return (
    <RecetaForm open={true} recipe={null} onClose={() => nav('..', { replace: true })} />
  )
}

