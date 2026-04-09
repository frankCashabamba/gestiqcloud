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

export type ImportadorDashboardStats = {
  total: number
  pendientes: number
  en_revision: number
  confirmados: number
  fallidos: number
}

export type ImportadorBatchSummary = {
  id: string
  estado: string
  total_items: number
  pending_items: number
  processing_items: number
  review_items: number
  confirmed_items: number
  failed_items: number
  progress_pct: number
  created_at: string
  updated_at: string
  completed_at: string | null
}

export type ImportadorDocumentSummary = {
  id: string
  nombre_archivo: string
  tipo_archivo: string
  tamanio_bytes: number | null
  tipo_documento_detectado: string | null
  confianza_clasificacion: number | null
  requiere_revision: boolean
  estado: string
  proveedor_detectado: string | null
  monto_total: number | null
  synced_recipe_id: string | null
  synced_sheets: Record<string, unknown> | null
  saved_as: string | null
  saved_record_id: string | null
  saved_at: string | null
  last_processing_reason: string | null
  last_learning_reprocess_at: string | null
  last_confirmation_mode: string | null
  created_at: string
  updated_at: string | null
}

export type ImportadorLearningQueueItem = {
  id: string
  nombre_archivo: string
  tipo_documento_detectado: string | null
  estado: string
  confianza_clasificacion: number | null
  recipe_snapshot_id: string | null
  updated_at: string
  snapshot_learning_version: number
  applied_learning_version: number
  version_lag: number
}

export type ImportadorLearningInsight = {
  source_doc_type: string
  document_type: string
  signals_count: number
  save_count: number
  confirm_count: number
  edit_count: number
  top_missing_fields: string[]
  top_changed_fields: string[]
  suggested_required_groups: string[][]
  suggested_support_fields: string[]
  suggested_confidence_threshold: number
  avg_success_confidence: number
  notes: string[]
}

export type ImportadorRoutingOverview = {
  tenant_id: string
  tenant_name: string | null
  dashboard: ImportadorDashboardStats
  recent_batches: ImportadorBatchSummary[]
  recent_documents: ImportadorDocumentSummary[]
  reprocess_queue: ImportadorLearningQueueItem[]
  learning_insights: ImportadorLearningInsight[]
}

export type RuntimeConfigEntry = {
  id: string
  module: string
  key: string
  label: string | null
  value_text: string | null
  value_list: string[]
  value_kind: 'text' | 'list' | 'json'
  updated_at: string
}

export type RuntimeConfigModule = {
  module: string
  title: string
  description: string | null
  editable: boolean
  entries: RuntimeConfigEntry[]
}

export type RuntimeConfigCatalog = {
  modules: RuntimeConfigModule[]
}

export type RoutingProfilePayload = Omit<RoutingProfile, 'id'>
export type RoutingRulePayload = Omit<RoutingRule, 'id'>
export type RoutingPreviewPayload = RoutingPreviewRequest
export type RuntimeConfigEntryPayload = {
  label: string | null
  value_text: string | null
  value_list: string[]
}

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

function normalizeOverviewDocument(input: Partial<ImportadorDocumentSummary>): ImportadorDocumentSummary {
  return {
    id: String(input.id || ''),
    nombre_archivo: String(input.nombre_archivo || ''),
    tipo_archivo: String(input.tipo_archivo || ''),
    tamanio_bytes: input.tamanio_bytes == null ? null : Number(input.tamanio_bytes),
    tipo_documento_detectado: input.tipo_documento_detectado ? String(input.tipo_documento_detectado) : null,
    confianza_clasificacion: input.confianza_clasificacion == null ? null : Number(input.confianza_clasificacion),
    requiere_revision: Boolean(input.requiere_revision),
    estado: String(input.estado || ''),
    proveedor_detectado: input.proveedor_detectado ? String(input.proveedor_detectado) : null,
    monto_total: input.monto_total == null ? null : Number(input.monto_total),
    synced_recipe_id: input.synced_recipe_id ? String(input.synced_recipe_id) : null,
    synced_sheets: input.synced_sheets && typeof input.synced_sheets === 'object' ? input.synced_sheets : null,
    saved_as: input.saved_as ? String(input.saved_as) : null,
    saved_record_id: input.saved_record_id ? String(input.saved_record_id) : null,
    saved_at: input.saved_at ? String(input.saved_at) : null,
    last_processing_reason: input.last_processing_reason ? String(input.last_processing_reason) : null,
    last_learning_reprocess_at: input.last_learning_reprocess_at ? String(input.last_learning_reprocess_at) : null,
    last_confirmation_mode: input.last_confirmation_mode ? String(input.last_confirmation_mode) : null,
    created_at: String(input.created_at || ''),
    updated_at: input.updated_at ? String(input.updated_at) : null,
  }
}

function normalizeBatchSummary(input: Partial<ImportadorBatchSummary>): ImportadorBatchSummary {
  return {
    id: String(input.id || ''),
    estado: String(input.estado || ''),
    total_items: Number(input.total_items ?? 0),
    pending_items: Number(input.pending_items ?? 0),
    processing_items: Number(input.processing_items ?? 0),
    review_items: Number(input.review_items ?? 0),
    confirmed_items: Number(input.confirmed_items ?? 0),
    failed_items: Number(input.failed_items ?? 0),
    progress_pct: Number(input.progress_pct ?? 0),
    created_at: String(input.created_at || ''),
    updated_at: String(input.updated_at || ''),
    completed_at: input.completed_at ? String(input.completed_at) : null,
  }
}

function normalizeLearningQueueItem(input: Partial<ImportadorLearningQueueItem>): ImportadorLearningQueueItem {
  return {
    id: String(input.id || ''),
    nombre_archivo: String(input.nombre_archivo || ''),
    tipo_documento_detectado: input.tipo_documento_detectado ? String(input.tipo_documento_detectado) : null,
    estado: String(input.estado || ''),
    confianza_clasificacion: input.confianza_clasificacion == null ? null : Number(input.confianza_clasificacion),
    recipe_snapshot_id: input.recipe_snapshot_id ? String(input.recipe_snapshot_id) : null,
    updated_at: String(input.updated_at || ''),
    snapshot_learning_version: Number(input.snapshot_learning_version ?? 0),
    applied_learning_version: Number(input.applied_learning_version ?? 0),
    version_lag: Number(input.version_lag ?? 0),
  }
}

function normalizeLearningInsight(input: Partial<ImportadorLearningInsight>): ImportadorLearningInsight {
  return {
    source_doc_type: String(input.source_doc_type || ''),
    document_type: String(input.document_type || ''),
    signals_count: Number(input.signals_count ?? 0),
    save_count: Number(input.save_count ?? 0),
    confirm_count: Number(input.confirm_count ?? 0),
    edit_count: Number(input.edit_count ?? 0),
    top_missing_fields: Array.isArray(input.top_missing_fields) ? input.top_missing_fields.map(String) : [],
    top_changed_fields: Array.isArray(input.top_changed_fields) ? input.top_changed_fields.map(String) : [],
    suggested_required_groups: Array.isArray(input.suggested_required_groups)
      ? input.suggested_required_groups.map((group) => Array.isArray(group) ? group.map(String) : [])
      : [],
    suggested_support_fields: Array.isArray(input.suggested_support_fields) ? input.suggested_support_fields.map(String) : [],
    suggested_confidence_threshold: Number(input.suggested_confidence_threshold ?? 0),
    avg_success_confidence: Number(input.avg_success_confidence ?? 0),
    notes: Array.isArray(input.notes) ? input.notes.map(String) : [],
  }
}

function normalizeOverview(input: Partial<ImportadorRoutingOverview>): ImportadorRoutingOverview {
  return {
    tenant_id: String(input.tenant_id || ''),
    tenant_name: input.tenant_name ? String(input.tenant_name) : null,
    dashboard: {
      total: Number(input.dashboard?.total ?? 0),
      pendientes: Number(input.dashboard?.pendientes ?? 0),
      en_revision: Number(input.dashboard?.en_revision ?? 0),
      confirmados: Number(input.dashboard?.confirmados ?? 0),
      fallidos: Number(input.dashboard?.fallidos ?? 0),
    },
    recent_batches: Array.isArray(input.recent_batches) ? input.recent_batches.map((batch) => normalizeBatchSummary(batch || {})) : [],
    recent_documents: Array.isArray(input.recent_documents) ? input.recent_documents.map((doc) => normalizeOverviewDocument(doc || {})) : [],
    reprocess_queue: Array.isArray(input.reprocess_queue) ? input.reprocess_queue.map((item) => normalizeLearningQueueItem(item || {})) : [],
    learning_insights: Array.isArray(input.learning_insights) ? input.learning_insights.map((item) => normalizeLearningInsight(item || {})) : [],
  }
}

function normalizeRuntimeConfigEntry(input: Partial<RuntimeConfigEntry>): RuntimeConfigEntry {
  return {
    id: String(input.id || ''),
    module: String(input.module || ''),
    key: String(input.key || ''),
    label: input.label ? String(input.label) : null,
    value_text: input.value_text ?? null,
    value_list: Array.isArray(input.value_list) ? input.value_list.map(String) : [],
    value_kind: (input.value_kind as RuntimeConfigEntry['value_kind']) || 'text',
    updated_at: String(input.updated_at || ''),
  }
}

function normalizeRuntimeConfigCatalog(input: Partial<RuntimeConfigCatalog>): RuntimeConfigCatalog {
  return {
    modules: Array.isArray(input.modules)
      ? input.modules.map((module) => ({
          module: String(module?.module || ''),
          title: String(module?.title || ''),
          description: module?.description ? String(module.description) : null,
          editable: module?.editable ?? true,
          entries: Array.isArray(module?.entries) ? module.entries.map((entry) => normalizeRuntimeConfigEntry(entry || {})) : [],
        }))
      : [],
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

export async function getImportadorRoutingOverview(tenantId: string, limit = 8): Promise<ImportadorRoutingOverview> {
  const params = new URLSearchParams({ tenant_id: tenantId, limit: String(limit) })
  const { data } = await api.get<Partial<ImportadorRoutingOverview>>(`${BASE}/overview?${params.toString()}`)
  return normalizeOverview(data || {})
}

export async function listRuntimeConfig(): Promise<RuntimeConfigCatalog> {
  const { data } = await api.get<Partial<RuntimeConfigCatalog>>(`${BASE}/runtime-config`)
  return normalizeRuntimeConfigCatalog(data || {})
}

export async function upsertRuntimeConfigEntry(
  module: string,
  key: string,
  payload: RuntimeConfigEntryPayload
): Promise<RuntimeConfigEntry> {
  const { data } = await api.put<Partial<RuntimeConfigEntry>>(
    `${BASE}/runtime-config/${encodeURIComponent(module)}/${encodeURIComponent(key)}`,
    payload
  )
  return normalizeRuntimeConfigEntry(data || {})
}

export async function deleteRuntimeConfigEntry(module: string, key: string): Promise<void> {
  await api.delete(`${BASE}/runtime-config/${encodeURIComponent(module)}/${encodeURIComponent(key)}`)
}

export async function resetRuntimeConfigModule(module: string): Promise<void> {
  await api.post(`${BASE}/runtime-config/${encodeURIComponent(module)}/reset`)
}

// ── Column Candidates ─────────────────────────────────────────────────────────

export type ColumnCandidate = {
  id: string
  alias: string
  alias_norm: string
  doc_type: string | null
  tenant_id: string | null
  seen_count: number
  first_seen_at: string
  last_seen_at: string
  canonical_field: string | null
  assigned_at: string | null
  assigned_by: string | null
}

function normalizeColumnCandidate(input: Partial<ColumnCandidate>): ColumnCandidate {
  return {
    id: String(input.id || ''),
    alias: String(input.alias || ''),
    alias_norm: String(input.alias_norm || ''),
    doc_type: input.doc_type ? String(input.doc_type) : null,
    tenant_id: input.tenant_id ? String(input.tenant_id) : null,
    seen_count: Number(input.seen_count ?? 1),
    first_seen_at: String(input.first_seen_at || ''),
    last_seen_at: String(input.last_seen_at || ''),
    canonical_field: input.canonical_field ? String(input.canonical_field) : null,
    assigned_at: input.assigned_at ? String(input.assigned_at) : null,
    assigned_by: input.assigned_by ? String(input.assigned_by) : null,
  }
}

export async function listColumnCandidates(unassignedOnly = false): Promise<ColumnCandidate[]> {
  const qs = unassignedOnly ? '?unassigned_only=true' : ''
  const { data } = await api.get<Array<Partial<ColumnCandidate>>>(`${BASE}/column-candidates${qs}`)
  return Array.isArray(data) ? data.map(normalizeColumnCandidate) : []
}

export async function assignColumnCandidate(id: string, canonicalField: string, assignedBy?: string): Promise<void> {
  await api.put(`${BASE}/column-candidates/${encodeURIComponent(id)}/assign`, {
    canonical_field: canonicalField,
    assigned_by: assignedBy ?? null,
  })
}

export async function deleteColumnCandidate(id: string): Promise<void> {
  await api.delete(`${BASE}/column-candidates/${encodeURIComponent(id)}`)
}

// ── Field Aliases ─────────────────────────────────────────────────────────────

export type FieldAlias = {
  id: string
  canonical_field: string
  alias: string
  tenant_id: string | null
  active: boolean
  priority: number
  source: string
  confirmed_count: number
  last_seen_at: string | null
}

function normalizeFieldAlias(input: Partial<FieldAlias>): FieldAlias {
  return {
    id: String(input.id || ''),
    canonical_field: String(input.canonical_field || ''),
    alias: String(input.alias || ''),
    tenant_id: input.tenant_id ? String(input.tenant_id) : null,
    active: Boolean(input.active ?? true),
    priority: Number(input.priority ?? 5),
    source: String(input.source || 'manual'),
    confirmed_count: Number(input.confirmed_count ?? 0),
    last_seen_at: input.last_seen_at ? String(input.last_seen_at) : null,
  }
}

export async function listFieldAliases(canonicalField?: string): Promise<FieldAlias[]> {
  const qs = canonicalField ? `?canonical_field=${encodeURIComponent(canonicalField)}` : ''
  const { data } = await api.get<Array<Partial<FieldAlias>>>(`${BASE}/field-aliases${qs}`)
  return Array.isArray(data) ? data.map(normalizeFieldAlias) : []
}

export async function createFieldAlias(payload: { canonical_field: string; alias: string; priority?: number }): Promise<void> {
  await api.post(`${BASE}/field-aliases`, payload)
}

export async function deleteFieldAlias(id: string): Promise<void> {
  await api.delete(`${BASE}/field-aliases/${encodeURIComponent(id)}`)
}

// ── Canonical Fields ──────────────────────────────────────────────────────────

export type CanonicalField = {
  name: string
  field_type: string
  projection_column: string | null
}

export async function listCanonicalFields(): Promise<CanonicalField[]> {
  const { data } = await api.get<CanonicalField[]>(`${BASE}/canonical-fields`)
  return Array.isArray(data)
    ? data.map((f) => ({ name: String(f.name || ''), field_type: String(f.field_type || 'text'), projection_column: f.projection_column ?? null }))
    : []
}
