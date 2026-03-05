import { useTranslation } from 'react-i18next'

type BadgeStyle = { background: string; color: string }

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'lost' | string | undefined
export type OpportunityStage = 'prospecting' | 'qualification' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost' | string | undefined

const leadStatusConfig: Record<string, BadgeStyle> = {
  new: { background: '#dbeafe', color: '#1e40af' },
  contacted: { background: '#fef3c7', color: '#92400e' },
  qualified: { background: '#d1fae5', color: '#065f46' },
  lost: { background: '#fee2e2', color: '#991b1b' },
}

const leadLabelKeys: Record<string, string> = {
  new: 'crm:status.new',
  contacted: 'crm:status.contacted',
  qualified: 'crm:status.qualified',
  lost: 'crm:status.lost',
}

const opportunityStageConfig: Record<string, BadgeStyle> = {
  prospecting: { background: '#e0e7ff', color: '#3730a3' },
  qualification: { background: '#dbeafe', color: '#1e40af' },
  proposal: { background: '#fef3c7', color: '#92400e' },
  negotiation: { background: '#fed7aa', color: '#9a3412' },
  closed_won: { background: '#dcfce7', color: '#166534' },
  closed_lost: { background: '#fee2e2', color: '#991b1b' },
}

const opportunityLabelKeys: Record<string, string> = {
  prospecting: 'crm:stage.prospecting',
  qualification: 'crm:stage.qualification',
  proposal: 'crm:stage.proposal',
  negotiation: 'crm:stage.negotiation',
  closed_won: 'crm:stage.closedWon',
  closed_lost: 'crm:stage.closedLost',
}

interface StatusBadgeProps {
  status?: LeadStatus | OpportunityStage
  type?: 'lead' | 'opportunity'
}

export default function StatusBadge({ status, type = 'lead' }: StatusBadgeProps) {
  const { t } = useTranslation('crm')
  const config = type === 'lead' ? leadStatusConfig : opportunityStageConfig
  const labelKeys = type === 'lead' ? leadLabelKeys : opportunityLabelKeys
  const normalizedStatus = (status || '').toLowerCase()
  const style: BadgeStyle =
    config[normalizedStatus] || { background: '#f3f4f6', color: '#111827' }
  const label = labelKeys[normalizedStatus] ? t(labelKeys[normalizedStatus].replace('crm:', '')) : (status || '-')

  return (
    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600, ...style }}>
      {label}
    </span>
  )
}
