import { apiFetch } from '../../lib/http'
import { TENANT_CRM } from '@shared/endpoints'
import type {
  Lead,
  Opportunity,
  Activity,
  CreateLeadRequest,
  UpdateLeadRequest,
  ConvertLeadRequest,
  CreateOpportunityRequest,
  UpdateOpportunityRequest,
  CreateActivityRequest,
  LeadListParams,
  OpportunityListParams,
  ActivityListParams,
  CRMDashboard,
} from './types'

export type {
  Lead,
  Opportunity,
  Activity,
  CreateLeadRequest,
  UpdateLeadRequest,
  ConvertLeadRequest,
  CreateOpportunityRequest,
  UpdateOpportunityRequest,
  CreateActivityRequest,
  LeadListParams,
  OpportunityListParams,
  ActivityListParams,
  CRMDashboard,
} from './types'

function buildQueryParams(params?: Record<string, any>): string {
  if (!params) return ''
  const filtered = Object.entries(params).filter(([_, v]) => v !== undefined && v !== null)
  if (filtered.length === 0) return ''
  const qs = new URLSearchParams(filtered.map(([k, v]) => [k, String(v)])).toString()
  return qs ? `?${qs}` : ''
}

export async function listLeads(params?: LeadListParams): Promise<Lead[]> {
  const queryString = buildQueryParams(params)
  const res = await apiFetch<Lead[] | { items?: Lead[] }>(`${TENANT_CRM.leads.base}${queryString}`)
  return Array.isArray(res) ? res : res.items || []
}

export async function getLead(id: string): Promise<Lead> {
  return apiFetch<Lead>(TENANT_CRM.leads.byId(id))
}

export async function createLead(data: CreateLeadRequest): Promise<Lead> {
  return apiFetch<Lead>(TENANT_CRM.leads.base, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateLead(id: string, data: UpdateLeadRequest): Promise<Lead> {
  return apiFetch<Lead>(TENANT_CRM.leads.byId(id), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteLead(id: string): Promise<void> {
  await apiFetch(TENANT_CRM.leads.byId(id), { method: 'DELETE' })
}

export async function convertLead(id: string, data: ConvertLeadRequest): Promise<{ lead: Lead; opportunity?: Opportunity; cliente_id?: string }> {
  return apiFetch(TENANT_CRM.leads.convert(id), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function listOpportunities(params?: OpportunityListParams): Promise<Opportunity[]> {
  const queryString = buildQueryParams(params)
  const res = await apiFetch<Opportunity[] | { items?: Opportunity[] }>(`${TENANT_CRM.opportunities.base}${queryString}`)
  return Array.isArray(res) ? res : res.items || []
}

export async function getOpportunity(id: string): Promise<Opportunity> {
  return apiFetch<Opportunity>(TENANT_CRM.opportunities.byId(id))
}

export async function createOpportunity(data: CreateOpportunityRequest): Promise<Opportunity> {
  return apiFetch<Opportunity>(TENANT_CRM.opportunities.base, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateOpportunity(id: string, data: UpdateOpportunityRequest): Promise<Opportunity> {
  return apiFetch<Opportunity>(TENANT_CRM.opportunities.byId(id), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteOpportunity(id: string): Promise<void> {
  await apiFetch(TENANT_CRM.opportunities.byId(id), { method: 'DELETE' })
}

export async function getDashboard(): Promise<CRMDashboard> {
  return apiFetch<CRMDashboard>(TENANT_CRM.dashboard)
}

export async function listActivities(params?: ActivityListParams): Promise<Activity[]> {
  const queryString = buildQueryParams(params)
  const res = await apiFetch<Activity[] | { items?: Activity[] }>(`${TENANT_CRM.activities.base}${queryString}`)
  return Array.isArray(res) ? res : res.items || []
}

export async function createActivity(data: CreateActivityRequest): Promise<Activity> {
  return apiFetch<Activity>(TENANT_CRM.activities.base, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
