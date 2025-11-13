/**
 * CRM Module Types
 */

import { UUID, Timestamp, PaginatedResponse } from './common'

export type LeadStatus = 
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'proposal'
  | 'negotiation'
  | 'won'
  | 'lost'

export type LeadSource = 
  | 'website'
  | 'referral'
  | 'social_media'
  | 'email'
  | 'phone'
  | 'event'
  | 'other'

export type Lead = {
  id: UUID
  tenant_id: UUID
  name: string
  company?: string
  email: string
  phone?: string
  status: LeadStatus
  source: LeadSource
  assigned_to?: UUID
  score?: number
  notes?: string
  custom_fields?: Record<string, unknown>
  created_at: Timestamp
  updated_at: Timestamp
  converted_at?: Timestamp
  opportunity_id?: UUID
}

export type LeadInput = Omit<Lead, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>

export type LeadUpdate = Partial<LeadInput>

export type OpportunityStage = 
  | 'qualification'
  | 'needs_analysis'
  | 'proposal'
  | 'negotiation'
  | 'closed_won'
  | 'closed_lost'

export type Opportunity = {
  id: UUID
  tenant_id: UUID
  lead_id?: UUID
  customer_id?: UUID
  title: string
  description?: string
  value: number
  currency: string
  probability: number
  stage: OpportunityStage
  expected_close_date?: string
  actual_close_date?: string
  assigned_to?: UUID
  lost_reason?: string
  custom_fields?: Record<string, unknown>
  created_at: Timestamp
  updated_at: Timestamp
}

export type OpportunityInput = Omit<Opportunity, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>

export type OpportunityUpdate = Partial<OpportunityInput>

export type Activity = {
  id: UUID
  tenant_id: UUID
  lead_id?: UUID
  opportunity_id?: UUID
  customer_id?: UUID
  type: ActivityType
  subject: string
  description?: string
  status: ActivityStatus
  due_date?: Timestamp
  completed_at?: Timestamp
  assigned_to?: UUID
  created_by: UUID
  created_at: Timestamp
  updated_at: Timestamp
}

export type ActivityType = 
  | 'call'
  | 'email'
  | 'meeting'
  | 'task'
  | 'note'
  | 'other'

export type ActivityStatus = 
  | 'pending'
  | 'completed'
  | 'cancelled'

export type ActivityInput = Omit<Activity, 'id' | 'tenant_id' | 'created_at' | 'updated_at' | 'created_by'>

export type CRMDashboard = {
  total_leads: number
  total_opportunities: number
  total_pipeline_value: number
  conversion_rate: number
  won_opportunities: number
  lost_opportunities: number
  leads_by_status: Record<LeadStatus, number>
  opportunities_by_stage: Record<OpportunityStage, number>
  recent_activities: Activity[]
  top_performers: Array<{
    user_id: UUID
    user_name: string
    opportunities_won: number
    total_value: number
  }>
}

export type Pipeline = {
  stages: Array<{
    stage: OpportunityStage
    opportunities: Opportunity[]
    total_value: number
    count: number
  }>
  total_value: number
  weighted_value: number
}

// Paginated responses
export type LeadListResponse = PaginatedResponse<Lead>
export type OpportunityListResponse = PaginatedResponse<Opportunity>
export type ActivityListResponse = PaginatedResponse<Activity>
