import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Edit2, DollarSign, TrendingUp } from 'lucide-react'
import StatusBadge, { OpportunityStage } from './StatusBadge'

interface Opportunity {
  id: number | string
  title: string
  value?: number
  probability?: number
  stage: OpportunityStage
}

interface OpportunityCardProps {
  opportunity: Opportunity
}

export default function OpportunityCard({ opportunity }: OpportunityCardProps) {
  const navigate = useNavigate()
  const probability = opportunity.probability || 0

  return (
    <div
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: 16,
        backgroundColor: '#fff',
        transition: 'box-shadow 0.2s',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1)')}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#111827' }}>{opportunity.title}</h3>
        </div>
        <StatusBadge status={opportunity.stage} type="opportunity" />
      </div>

      {opportunity.value !== undefined && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#059669', fontSize: 18, fontWeight: 600 }}>
          <DollarSign size={18} />
          <span>{new Intl.NumberFormat('es-BO', { minimumFractionDigits: 2 }).format(opportunity.value)}</span>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, color: '#6b7280', fontSize: 13 }}>
          <TrendingUp size={14} />
          <span>Probabilidad: {probability}%</span>
        </div>
        <div style={{ width: '100%', height: 6, backgroundColor: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
          <div
            style={{
              width: `${probability}%`,
              height: '100%',
              backgroundColor: probability > 75 ? '#10b981' : probability > 50 ? '#f59e0b' : '#6b7280',
              transition: 'width 0.3s',
            }}
          />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button
          onClick={() => navigate(`/crm/opportunities/${opportunity.id}/edit`)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '6px 12px',
            fontSize: 13,
            backgroundColor: '#f3f4f6',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontWeight: 500,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#e5e7eb')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#f3f4f6')}
        >
          <Edit2 size={14} />
          Editar
        </button>
      </div>
    </div>
  )
}
