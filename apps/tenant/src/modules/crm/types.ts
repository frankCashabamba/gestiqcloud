export enum LeadStatus {
  NEW = 'new',
  CONTACTED = 'contacted',
  QUALIFIED = 'qualified',
  LOST = 'lost',
  CONVERTED = 'converted',
}

export enum LeadSource {
  WEBSITE = 'website',
  REFERRAL = 'referral',
  SOCIAL_MEDIA = 'social_media',
  EMAIL = 'email',
  PHONE = 'phone',
  EVENT = 'event',
  OTHER = 'other',
}

export enum OpportunityStage {
  PROSPECTING = 'prospecting',
  QUALIFICATION = 'qualification',
  PROPOSAL = 'proposal',
  NEGOTIATION = 'negotiation',
  CLOSED_WON = 'closed_won',
  CLOSED_LOST = 'closed_lost',
}

export enum ActivityType {
  CALL = 'call',
  EMAIL = 'email',
  MEETING = 'meeting',
  TASK = 'task',
  NOTE = 'note',
}

export enum ActivityStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export type Lead = {
  id: string
  tenant_id: string
  name: string
  email?: string
  phone?: string
  company?: string
  position?: string
  source: LeadSource
  status: LeadStatus
  score?: number
  notes?: string
  assigned_to?: string
  created_at: string
  updated_at?: string
}

export type Opportunity = {
  id: string
  tenant_id: string
  lead_id?: string
  name: string
  description?: string
  value: number
  currency?: string
  stage: OpportunityStage
  probability?: number
  expected_close_date?: string
  actual_close_date?: string
  assigned_to?: string
  cliente_id?: string
  created_at: string
  updated_at?: string
}

export type Activity = {
  id: string
  tenant_id: string
  lead_id?: string
  opportunity_id?: string
  type: ActivityType
  subject: string
  description?: string
  status: ActivityStatus
  due_date?: string
  completed_at?: string
  assigned_to?: string
  created_by?: string
  created_at: string
  updated_at?: string
}

export type CreateLeadRequest = Omit<Lead, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>

export type UpdateLeadRequest = Partial<CreateLeadRequest>

export type ConvertLeadRequest = {
  create_opportunity?: boolean
  opportunity_name?: string
  opportunity_value?: number
  create_cliente?: boolean
}

export type CreateOpportunityRequest = Omit<Opportunity, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>

export type UpdateOpportunityRequest = Partial<CreateOpportunityRequest>

export type CreateActivityRequest = Omit<Activity, 'id' | 'tenant_id' | 'created_at' | 'updated_at' | 'completed_at'>

export type LeadListParams = {
  status?: LeadStatus
  source?: LeadSource
  assigned_to?: string
  limit?: number
  offset?: number
}

export type OpportunityListParams = {
  stage?: OpportunityStage
  assigned_to?: string
  cliente_id?: string
  limit?: number
  offset?: number
}

export type ActivityListParams = {
  type?: ActivityType
  status?: ActivityStatus
  lead_id?: string
  opportunity_id?: string
  assigned_to?: string
  limit?: number
  offset?: number
}

export type CRMDashboard = {
  leads: {
    total: number
    by_status: Record<LeadStatus, number>
    by_source: Record<LeadSource, number>
    recent: Lead[]
  }
  opportunities: {
    total: number
    total_value: number
    by_stage: Record<OpportunityStage, number>
    win_rate: number
    recent: Opportunity[]
  }
  activities: {
    total: number
    pending: number
    overdue: number
    recent: Activity[]
  }
}
