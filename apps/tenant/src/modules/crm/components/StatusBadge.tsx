type BadgeStyle = { background: string; color: string; label: string }

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'lost' | string | undefined
export type OpportunityStage = 'prospecting' | 'qualification' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost' | string | undefined

const leadStatusConfig: Record<string, BadgeStyle> = {
  new: { background: '#dbeafe', color: '#1e40af', label: 'Nuevo' },
  contacted: { background: '#fef3c7', color: '#92400e', label: 'Contactado' },
  qualified: { background: '#d1fae5', color: '#065f46', label: 'Calificado' },
  lost: { background: '#fee2e2', color: '#991b1b', label: 'Perdido' },
}

const opportunityStageConfig: Record<string, BadgeStyle> = {
  prospecting: { background: '#e0e7ff', color: '#3730a3', label: 'Prospección' },
  qualification: { background: '#dbeafe', color: '#1e40af', label: 'Calificación' },
  proposal: { background: '#fef3c7', color: '#92400e', label: 'Propuesta' },
  negotiation: { background: '#fed7aa', color: '#9a3412', label: 'Negociación' },
  closed_won: { background: '#dcfce7', color: '#166534', label: 'Ganada' },
  closed_lost: { background: '#fee2e2', color: '#991b1b', label: 'Perdida' },
}

interface StatusBadgeProps {
  status?: LeadStatus | OpportunityStage
  type?: 'lead' | 'opportunity'
}

export default function StatusBadge({ status, type = 'lead' }: StatusBadgeProps) {
  const config = type === 'lead' ? leadStatusConfig : opportunityStageConfig
  const normalizedStatus = (status || '').toLowerCase()
  const style: BadgeStyle =
    config[normalizedStatus] || { background: '#f3f4f6', color: '#111827', label: status || '-' }

  return (
    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600, ...style }}>
      {style.label}
    </span>
  )
}
