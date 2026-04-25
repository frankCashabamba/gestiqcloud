import React from 'react'
import { useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import PageContainer from '../../components/PageContainer'

export default function BancoList() {
  const nav = useNavigate()
  return (
    <PageContainer>
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div>Bank accounts module coming soon</div>
    </PageContainer>
  )
}
