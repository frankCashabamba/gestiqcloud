import api from '../../shared/api/client'

export type RoutingDestination = 'recipe' | 'expense' | 'supplier_invoice'
export type RoutingSourceKind = 'doc_type' | 'category'
export type RoutingScopeKind = 'system' | 'sector' | 'tenant'
export type RoutingMatchScope = 'destination_override' | 'tenant' | 'sector' | 'system' | 'fallback'

export type RoutingProfile = {
  id: string
  code: string
  document_type: string
  description: string | null
  suggested_destination: RoutingDestination | null
  required_groups: string[][]
  support_fields: string[]
  explanation_fields: string[]
  blocked: boolean
  confidence_threshold: number
  active: boolean
}

export type RoutingRule = {
  id: string
  scope_kind: RoutingScopeKind
  tenant_id: string | null
  sector: string | null
  source_kind: RoutingSourceKind
  source_key: string
  profile_code: string
  priority: number
  active: boolean
}

export type RoutingDecisionPreview = {
  document_type: string
  confidence: number
  required_fields_ok: boolean
  missing_fields: string[]
  suggested_destination: RoutingDestination | null
  reason: string
  needs_human_review: boolean
  source_doc_type: string | null
  source_category: string | null
}

export type RoutingPreviewRequest = {
  document_id: string | null
  scope_kind: RoutingScopeKind
  tenant_id: string | null
  sector: string | null
  source_doc_type: string | null
  source_category: string | null
  ai_confidence: number
  extracted_data: Record<string, unknown>
  canonical_fields: Record<string, unknown>
  requires_review: boolean
  destination_override: RoutingDestination | null
}

export type RoutingPreviewResponse = {
  decision: RoutingDecisionPreview
  profile_code: string
  matched_by: string
  matched_scope: RoutingMatchScope
  rule_source_kind: RoutingSourceKind | null
  rule_source_key: string | null
  resolved_sector: string
  document_id: string | null
  document_name: string | null
  tenant_id: string | null
}

export type RoutingPreviewDocument = {
  id: string
  tenant_id: string
  nombre_archivo: string
  tipo_documento_detectado: string | null
  estado: string
  created_at: string
  proveedor_detectado: string | null
  monto_total: number | null
}

export type RoutingProfilePayload = Omit<RoutingProfile, 'id'>
export type RoutingRulePayload = Omit<RoutingRule, 'id'>
export type RoutingPreviewPayload = RoutingPreviewRequest

const BASE = '/v1/admin/importador/routing'

function normalizeProfile(input: Partial<RoutingProfile>): RoutingProfile {
  return {
    id: String(input.id || ''),
    code: String(input.code || ''),
    document_type: String(input.document_type || ''),
    description: input.description ?? null,
    suggested_destination: (input.suggested_destination as RoutingDestination | null) ?? null,
    required_groups: Array.isArray(input.required_groups) ? input.required_groups.map((group) => Array.isArray(group) ? group.map(String) : []) : [],
    support_fields: Array.isArray(input.support_fields) ? input.support_fields.map(String) : [],
    explanation_fields: Array.isArray(input.explanation_fields) ? input.explanation_fields.map(String) : [],
    blocked: Boolean(input.blocked),
    confidence_threshold: Number(input.confidence_threshold ?? 0.8),
    active: input.active ?? true,
  }
}

function normalizeRule(input: Partial<RoutingRule>): RoutingRule {
  return {
    id: String(input.id || ''),
    scope_kind: (input.scope_kind as RoutingScopeKind) || 'system',
    tenant_id: input.tenant_id ? String(input.tenant_id) : null,
    sector: input.sector ? String(input.sector) : null,
    source_kind: (input.source_kind as RoutingSourceKind) || 'doc_type',
    source_key: String(input.source_key || ''),
    profile_code: String(input.profile_code || ''),
    priority: Number(input.priority ?? 100),
    active: input.active ?? true,
  }
}

function normalizePreviewDecision(input: Partial<RoutingDecisionPreview>): RoutingDecisionPreview {
  return {
    document_type: String(input.document_type || ''),
    confidence: Number(input.confidence ?? 0),
    required_fields_ok: Boolean(input.required_fields_ok),
    missing_fields: Array.isArray(input.missing_fields) ? input.missing_fields.map(String) : [],
    suggested_destination: (input.suggested_destination as RoutingDestination | null) ?? null,
    reason: String(input.reason || ''),
    needs_human_review: Boolean(input.needs_human_review),
    source_doc_type: input.source_doc_type ? String(input.source_doc_type) : null,
    source_category: input.source_category ? String(input.source_category) : null,
  }
}

function normalizePreviewResponse(input: Partial<RoutingPreviewResponse>): RoutingPreviewResponse {
  return {
    decision: normalizePreviewDecision(input.decision || {}),
    profile_code: String(input.profile_code || ''),
    matched_by: String(input.matched_by || ''),
    matched_scope: (input.matched_scope as RoutingMatchScope) || 'fallback',
    rule_source_kind: (input.rule_source_kind as RoutingSourceKind | null) ?? null,
    rule_source_key: input.rule_source_key ? String(input.rule_source_key) : null,
    resolved_sector: String(input.resolved_sector || ''),
    document_id: input.document_id ? String(input.document_id) : null,
    document_name: input.document_name ? String(input.document_name) : null,
    tenant_id: input.tenant_id ? String(input.tenant_id) : null,
  }
}

function normalizePreviewDocument(input: Partial<RoutingPreviewDocument>): RoutingPreviewDocument {
  return {
    id: String(input.id || ''),
    tenant_id: String(input.tenant_id || ''),
    nombre_archivo: String(input.nombre_archivo || ''),
    tipo_documento_detectado: input.tipo_documento_detectado ? String(input.tipo_documento_detectado) : null,
    estado: String(input.estado || ''),
    created_at: String(input.created_at || ''),
    proveedor_detectado: input.proveedor_detectado ? String(input.proveedor_detectado) : null,
    monto_total: input.monto_total == null ? null : Number(input.monto_total),
  }
}

export async function listRoutingProfiles(): Promise<RoutingProfile[]> {
  const { data } = await api.get<Array<Partial<RoutingProfile>>>(`${BASE}/profiles`)
  return Array.isArray(data) ? data.map(normalizeProfile) : []
}

export async function createRoutingProfile(payload: RoutingProfilePayload): Promise<RoutingProfile> {
  const { data } = await api.post<{ ok: boolean; item: Partial<RoutingProfile> }>(`${BASE}/profiles`, payload)
  return normalizeProfile(data?.item || payload)
}

export async function updateRoutingProfile(code: string, payload: RoutingProfilePayload): Promise<RoutingProfile> {
  const { data } = await api.put<{ ok: boolean; item: Partial<RoutingProfile> }>(`${BASE}/profiles/${encodeURIComponent(code)}`, payload)
  return normalizeProfile(data?.item || payload)
}

export async function deleteRoutingProfile(code: string): Promise<void> {
  await api.delete(`${BASE}/profiles/${encodeURIComponent(code)}`)
}

export async function listRoutingRules(scopeKind?: RoutingScopeKind | ''): Promise<RoutingRule[]> {
  const qs = scopeKind ? `?scope_kind=${encodeURIComponent(scopeKind)}` : ''
  const { data } = await api.get<Array<Partial<RoutingRule>>>(`${BASE}/rules${qs}`)
  return Array.isArray(data) ? data.map(normalizeRule) : []
}

export async function createRoutingRule(payload: RoutingRulePayload): Promise<RoutingRule> {
  const { data } = await api.post<{ ok: boolean; item: Partial<RoutingRule> }>(`${BASE}/rules`, payload)
  return normalizeRule(data?.item || payload)
}

export async function updateRoutingRule(id: string, payload: RoutingRulePayload): Promise<RoutingRule> {
  const { data } = await api.put<{ ok: boolean; item: Partial<RoutingRule> }>(`${BASE}/rules/${encodeURIComponent(id)}`, payload)
  return normalizeRule(data?.item || payload)
}

export async function deleteRoutingRule(id: string): Promise<void> {
  await api.delete(`${BASE}/rules/${encodeURIComponent(id)}`)
}

export async function previewRouting(payload: RoutingPreviewPayload): Promise<RoutingPreviewResponse> {
  const { data } = await api.post<Partial<RoutingPreviewResponse>>(`${BASE}/preview`, payload)
  return normalizePreviewResponse(data || {})
}

export async function listRoutingPreviewDocuments(tenantId: string, q?: string): Promise<RoutingPreviewDocument[]> {
  const params = new URLSearchParams({ tenant_id: tenantId })
  if (q && q.trim()) params.set('q', q.trim())
  const { data } = await api.get<Array<Partial<RoutingPreviewDocument>>>(`${BASE}/documents?${params.toString()}`)
  return Array.isArray(data) ? data.map(normalizePreviewDocument) : []
}
