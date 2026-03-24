import React from 'react'
import { useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'

export default function BancoList() {
  const nav = useNavigate()
  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div>Bank accounts module coming soon</div>
    </div>
  )
}
