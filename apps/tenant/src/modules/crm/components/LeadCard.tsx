import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Edit2, Mail, Building2 } from 'lucide-react'
import StatusBadge, { LeadStatus } from './StatusBadge'

interface Lead {
  id: number | string
  name: string
  company?: string
  email?: string
  status: LeadStatus
}

interface LeadCardProps {
  lead: Lead
}

export default function LeadCard({ lead }: LeadCardProps) {
  const navigate = useNavigate()

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
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#111827' }}>{lead.name}</h3>
        </div>
        <StatusBadge status={lead.status} type="lead" />
      </div>

      {lead.company && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#6b7280', fontSize: 14 }}>
          <Building2 size={16} />
          <span>{lead.company}</span>
        </div>
      )}

      {lead.email && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#6b7280', fontSize: 14 }}>
          <Mail size={16} />
          <span>{lead.email}</span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button
          onClick={() => navigate(`/crm/leads/${lead.id}/edit`)}
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
