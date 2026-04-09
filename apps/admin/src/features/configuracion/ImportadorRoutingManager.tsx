import React, { useCallback, useEffect, useMemo, useState } from 'react'

import { getErrorMessage, useToast } from '../../shared/toast'
import {
  assignColumnCandidate,
  createFieldAlias,
  createRoutingProfile,
  createRoutingRule,
  deleteColumnCandidate,
  deleteFieldAlias,
  deleteRoutingProfile,
  deleteRoutingRule,
  deleteRuntimeConfigEntry,
  getImportadorRoutingOverview,
  listCanonicalFields,
  listColumnCandidates,
  listFieldAliases,
  listRoutingProfiles,
  listRoutingPreviewDocuments,
  listRoutingRules,
  listRuntimeConfig,
  previewRouting,
  resetRuntimeConfigModule,
  upsertRuntimeConfigEntry,
  type CanonicalField,
  type ColumnCandidate,
  type ImportadorRoutingOverview,
  type FieldAlias,
  type RuntimeConfigCatalog,
  type RuntimeConfigEntry,
  type RuntimeConfigModule,
  type RoutingDestination,
  type RoutingPreviewDocument,
  type RoutingPreviewPayload,
  type RoutingPreviewResponse,
  type RoutingProfile,
  type RoutingProfilePayload,
  type RoutingRule,
  type RoutingRulePayload,
  type RoutingScopeKind,
  updateRoutingProfile,
  updateRoutingRule,
} from '../../services/configuracion/importador-routing'
import { getEmpresas } from '../../services/empresa'
import '../../pages/admin-panel.css'
import './importador-routing.css'

type ProfileFormState = {
  code: string
  document_type: string
  description: string
  suggested_destination: RoutingDestination | ''
  required_groups_text: string
  support_fields_text: string
  explanation_fields_text: string
  blocked: boolean
  confidence_threshold: string
  active: boolean
}

type RuleFormState = {
  scope_kind: RoutingScopeKind
  tenant_id: string
  sector: string
  source_kind: 'doc_type' | 'category'
  source_key: string
  profile_code: string
  priority: string
  active: boolean
}

type PreviewFormState = {
  document_id: string
  scope_kind: RoutingScopeKind
  tenant_id: string
  sector: string
  source_doc_type: string
  source_category: string
  ai_confidence: string
  destination_override: RoutingDestination | ''
  requires_review: boolean
  extracted_data_text: string
  canonical_fields_text: string
}

type AdminCompanyOption = {
  id: string
  name: string
  slug: string
}

type PreviewPreset = {
  key: string
  label: string
  description: string
  patch: Partial<PreviewFormState>
}

type RuntimeEntryFormState = {
  label: string
  value_text: string
  value_list_text: string
}

type RuntimeEntryEditState = {
  module: string
  key: string
  value_kind: RuntimeConfigEntry['value_kind']
}

type MainTab = 'estado' | 'preview' | 'routing' | 'runtime' | 'vocabulario'

const PROFILE_DEFAULTS: ProfileFormState = {
  code: '',
  document_type: '',
  description: '',
  suggested_destination: '',
  required_groups_text: 'issue_date\ntotal_amount',
  support_fields_text: '',
  explanation_fields_text: '',
  blocked: false,
  confidence_threshold: '0.80',
  active: true,
}

const RULE_DEFAULTS: RuleFormState = {
  scope_kind: 'system',
  tenant_id: '',
  sector: '',
  source_kind: 'doc_type',
  source_key: '',
  profile_code: '',
  priority: '100',
  active: true,
}

const PREVIEW_DEFAULTS: PreviewFormState = {
  document_id: '',
  scope_kind: 'system',
  tenant_id: '',
  sector: '',
  source_doc_type: 'INVOICE',
  source_category: '',
  ai_confidence: '0.90',
  destination_override: '',
  requires_review: false,
  extracted_data_text: '{\n  "vendor": "Proveedor Demo",\n  "issue_date": "2026-03-27",\n  "total_amount": 125.5,\n  "concept": "Mantenimiento"\n}',
  canonical_fields_text: '{\n  "doc_number": "A-1023"\n}',
}

const PREVIEW_PRESETS: PreviewPreset[] = [
  {
    key: 'supplier_invoice',
    label: 'Factura proveedor',
    description: 'Proveedor, fecha, subtotal, IVA y total.',
    patch: {
      source_doc_type: 'INVOICE',
      source_category: 'invoice',
      destination_override: '',
      extracted_data_text:
        '{\n  "vendor": "Proveedor Demo",\n  "vendor_tax_id": "A12345678",\n  "issue_date": "2026-03-27",\n  "subtotal": 100,\n  "tax_amount": 21,\n  "total_amount": 121\n}',
      canonical_fields_text: '{\n  "doc_number": "F-2026-001"\n}',
    },
  },
  {
    key: 'expense_receipt',
    label: 'Ticket gasto',
    description: 'Gasto simple con concepto y total.',
    patch: {
      source_doc_type: 'RECEIPT',
      source_category: 'receipt',
      destination_override: 'expense',
      extracted_data_text:
        '{\n  "vendor": "Gasolinera Centro",\n  "issue_date": "2026-03-27",\n  "total_amount": 42.75,\n  "concept": "Combustible"\n}',
      canonical_fields_text: '{\n  "doc_number": "TK-8891"\n}',
    },
  },
  {
    key: 'recipe_sheet',
    label: 'Ficha receta',
    description: 'Receta o escandallo con lineas.',
    patch: {
      source_doc_type: 'RECIPE_SHEET',
      source_category: 'recipe',
      destination_override: 'recipe',
      extracted_data_text:
        '{\n  "rows": 4,\n  "line_items": [\n    { "name": "Harina", "qty": 1.5, "unit": "kg" },\n    { "name": "Agua", "qty": 0.9, "unit": "l" }\n  ]\n}',
      canonical_fields_text: '{\n  "doc_number": "REC-001"\n}',
    },
  },
]

function parseCsvLike(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseRequiredGroups(text: string): string[][] {
  return text
    .split('\n')
    .map((line) =>
      line
        .split('|')
        .map((item) => item.trim())
        .filter(Boolean)
    )
    .filter((group) => group.length > 0)
}

function stringifyRequiredGroups(groups: string[][]): string {
  return groups.map((group) => group.join(' | ')).join('\n')
}

function parseJsonObject(text: string, fieldName: string): Record<string, unknown> {
  const trimmed = text.trim()
  if (!trimmed) return {}
  try {
    const parsed = JSON.parse(trimmed)
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error(`${fieldName} debe ser un objeto JSON`)
    }
    return parsed as Record<string, unknown>
  } catch (error: any) {
    throw new Error(`${fieldName}: ${error?.message || 'JSON invalido'}`)
  }
}

function stringifyFields(fields: string[]): string {
  return fields.join(', ')
}

function buildProfilePayload(form: ProfileFormState): RoutingProfilePayload {
  return {
    code: form.code.trim().toLowerCase(),
    document_type: form.document_type.trim(),
    description: form.description.trim() || null,
    suggested_destination: form.suggested_destination || null,
    required_groups: parseRequiredGroups(form.required_groups_text),
    support_fields: parseCsvLike(form.support_fields_text),
    explanation_fields: parseCsvLike(form.explanation_fields_text),
    blocked: form.blocked,
    confidence_threshold: Number(form.confidence_threshold || '0.8'),
    active: form.active,
  }
}

function buildRulePayload(form: RuleFormState): RoutingRulePayload {
  return {
    scope_kind: form.scope_kind,
    tenant_id: form.scope_kind === 'tenant' ? form.tenant_id.trim() || null : null,
    sector: form.scope_kind === 'sector' ? form.sector.trim() || null : null,
    source_kind: form.source_kind,
    source_key: form.source_key.trim().toUpperCase(),
    profile_code: form.profile_code.trim().toLowerCase(),
    priority: Number(form.priority || '100'),
    active: form.active,
  }
}

function buildPreviewPayload(form: PreviewFormState): RoutingPreviewPayload {
  return {
    document_id: form.document_id.trim() || null,
    scope_kind: form.scope_kind,
    tenant_id: form.scope_kind === 'tenant' ? form.tenant_id.trim() || null : null,
    sector: form.scope_kind === 'sector' ? form.sector.trim() || null : null,
    source_doc_type: form.source_doc_type.trim() || null,
    source_category: form.source_category.trim() || null,
    ai_confidence: Number(form.ai_confidence || '0.9'),
    extracted_data: parseJsonObject(form.extracted_data_text, 'Extracted data'),
    canonical_fields: parseJsonObject(form.canonical_fields_text, 'Canonical fields'),
    requires_review: form.requires_review,
    destination_override: form.destination_override || null,
  }
}

function profileToForm(profile: RoutingProfile): ProfileFormState {
  return {
    code: profile.code,
    document_type: profile.document_type,
    description: profile.description || '',
    suggested_destination: profile.suggested_destination || '',
    required_groups_text: stringifyRequiredGroups(profile.required_groups),
    support_fields_text: stringifyFields(profile.support_fields),
    explanation_fields_text: stringifyFields(profile.explanation_fields),
    blocked: profile.blocked,
    confidence_threshold: String(profile.confidence_threshold),
    active: profile.active,
  }
}

function ruleToForm(rule: RoutingRule): RuleFormState {
  return {
    scope_kind: rule.scope_kind,
    tenant_id: rule.tenant_id || '',
    sector: rule.sector || '',
    source_kind: rule.source_kind,
    source_key: rule.source_key,
    profile_code: rule.profile_code,
    priority: String(rule.priority),
    active: rule.active,
  }
}

function StatCard({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="routing-stat-card rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{helper}</div>
    </div>
  )
}

function normalizeCompanyOption(input: any): AdminCompanyOption | null {
  const id = String(input?.id ?? '').trim()
  const name = String(input?.name ?? input?.nombre ?? '').trim()
  if (!id || !name) return null
  return {
    id,
    name,
    slug: String(input?.slug ?? '').trim(),
  }
}

function runtimeEntryToForm(entry: RuntimeConfigEntry): RuntimeEntryFormState {
  return {
    label: entry.label || '',
    value_text: entry.value_text || '',
    value_list_text: entry.value_list.join('\n'),
  }
}

function parseRuntimeList(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function runtimeEntryValuePreview(entry: RuntimeConfigEntry): string {
  if (entry.value_kind === 'list') {
    return entry.value_list.join(', ')
  }
  return entry.value_text || '—'
}

export default function ImportadorRoutingManager() {
  const [profiles, setProfiles] = useState<RoutingProfile[]>([])
  const [rules, setRules] = useState<RoutingRule[]>([])
  const [companies, setCompanies] = useState<AdminCompanyOption[]>([])
  const [previewDocuments, setPreviewDocuments] = useState<RoutingPreviewDocument[]>([])
  const [overview, setOverview] = useState<ImportadorRoutingOverview | null>(null)
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfigCatalog>({ modules: [] })
  const [mainTab, setMainTab] = useState<MainTab>('estado')
  const [loading, setLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [runtimeLoading, setRuntimeLoading] = useState(false)
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingRule, setSavingRule] = useState(false)
  const [savingRuntimeEntry, setSavingRuntimeEntry] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scopeFilter, setScopeFilter] = useState<RoutingScopeKind | ''>('')
  const [profileForm, setProfileForm] = useState<ProfileFormState>(PROFILE_DEFAULTS)
  const [ruleForm, setRuleForm] = useState<RuleFormState>(RULE_DEFAULTS)
  const [previewForm, setPreviewForm] = useState<PreviewFormState>(PREVIEW_DEFAULTS)
  const [previewResult, setPreviewResult] = useState<RoutingPreviewResponse | null>(null)
  const [companyQuery, setCompanyQuery] = useState('')
  const [documentQuery, setDocumentQuery] = useState('')
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [editingProfileCode, setEditingProfileCode] = useState<string | null>(null)
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [editingRuntimeEntry, setEditingRuntimeEntry] = useState<RuntimeEntryEditState | null>(null)
  const [runtimeForm, setRuntimeForm] = useState<RuntimeEntryFormState>({ label: '', value_text: '', value_list_text: '' })
  const [runtimeModuleFilter, setRuntimeModuleFilter] = useState('')
  // Vocabulario
  const [vocabTab, setVocabTab] = useState<'candidates' | 'aliases'>('candidates')
  const [candidates, setCandidates] = useState<ColumnCandidate[]>([])
  const [aliases, setAliases] = useState<FieldAlias[]>([])
  const [canonicalFields, setCanonicalFields] = useState<CanonicalField[]>([])
  const [vocabLoading, setVocabLoading] = useState(false)
  const [unassignedOnly, setUnassignedOnly] = useState(true)
  const [assigningId, setAssigningId] = useState<string | null>(null)
  const [assignValue, setAssignValue] = useState('')
  const [newAliasCanonical, setNewAliasCanonical] = useState('')
  const [newAliasValue, setNewAliasValue] = useState('')
  const [savingAlias, setSavingAlias] = useState(false)
  const { show } = useToast()

  const success = useCallback((message: string) => {
    show(message, 'success')
  }, [show])

  const toastError = useCallback((message: string) => {
    show(message, 'error')
  }, [show])

  const loadAll = useCallback(async (currentScope: RoutingScopeKind | '' = scopeFilter) => {
    try {
      setLoading(true)
      setError(null)
      const [profilesData, rulesData, companiesData] = await Promise.all([
        listRoutingProfiles(),
        listRoutingRules(currentScope),
        getEmpresas(),
      ])
      setProfiles(profilesData)
      setRules(rulesData)
      setCompanies(
        (Array.isArray(companiesData) ? companiesData : [])
          .map(normalizeCompanyOption)
          .filter((item): item is AdminCompanyOption => Boolean(item))
      )
    } catch (err: any) {
      const message = getErrorMessage(err)
      setError(message)
      toastError(message)
    } finally {
      setLoading(false)
    }
  }, [scopeFilter, toastError])

  const loadVocab = useCallback(async (currentUnassigned = unassignedOnly) => {
    try {
      setVocabLoading(true)
      const [candidatesData, aliasesData, fieldsData] = await Promise.all([
        listColumnCandidates(currentUnassigned),
        listFieldAliases(),
        listCanonicalFields(),
      ])
      setCandidates(candidatesData)
      setAliases(aliasesData)
      setCanonicalFields(fieldsData)
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setVocabLoading(false)
    }
  }, [unassignedOnly, toastError])

  const loadOverview = useCallback(async (tenantId: string) => {
    const trimmedTenantId = tenantId.trim()
    if (!trimmedTenantId) {
      setOverview(null)
      return
    }
    try {
      setOverviewLoading(true)
      const data = await getImportadorRoutingOverview(trimmedTenantId)
      setOverview(data)
    } catch (err: any) {
      toastError(getErrorMessage(err))
      setOverview(null)
    } finally {
      setOverviewLoading(false)
    }
  }, [toastError])

  const loadRuntimeConfig = useCallback(async () => {
    try {
      setRuntimeLoading(true)
      const data = await listRuntimeConfig()
      setRuntimeConfig(data)
    } catch (err: any) {
      toastError(getErrorMessage(err))
      setRuntimeConfig({ modules: [] })
    } finally {
      setRuntimeLoading(false)
    }
  }, [toastError])

  const handleAssignCandidate = useCallback(async (id: string, canonicalField: string) => {
    if (!canonicalField) return
    try {
      await assignColumnCandidate(id, canonicalField)
      success(`Asignado a "${canonicalField}" y promovido a aliases`)
      setAssigningId(null)
      setAssignValue('')
      await loadVocab()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [loadVocab, success, toastError])

  const handleDeleteCandidate = useCallback(async (id: string, alias: string) => {
    if (!window.confirm(`¿Descartar columna "${alias}"?`)) return
    try {
      await deleteColumnCandidate(id)
      success('Columna descartada')
      await loadVocab()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [loadVocab, success, toastError])

  const handleCreateAlias = useCallback(async () => {
    if (!newAliasCanonical.trim() || !newAliasValue.trim()) return
    setSavingAlias(true)
    try {
      await createFieldAlias({ canonical_field: newAliasCanonical.trim(), alias: newAliasValue.trim() })
      success('Alias creado')
      setNewAliasValue('')
      await loadVocab()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSavingAlias(false)
    }
  }, [newAliasCanonical, newAliasValue, loadVocab, success, toastError])

  const handleDeleteAlias = useCallback(async (id: string, alias: string) => {
    if (!window.confirm(`¿Eliminar alias "${alias}"?`)) return
    try {
      await deleteFieldAlias(id)
      success('Alias eliminado')
      await loadVocab()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [loadVocab, success, toastError])

  const handleDeleteProfile = useCallback(async (profile: RoutingProfile) => {
    if (!window.confirm(`¿Eliminar perfil ${profile.code}?`)) return
    try {
      await deleteRoutingProfile(profile.code)
      success('Perfil eliminado')
      if (editingProfileCode === profile.code) {
        setEditingProfileCode(null)
        setProfileForm(PROFILE_DEFAULTS)
      }
      await loadAll()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [editingProfileCode, loadAll, success, toastError])

  const handleDeleteRule = useCallback(async (rule: RoutingRule) => {
    if (!window.confirm(`¿Eliminar regla ${rule.source_kind}:${rule.source_key}?`)) return
    try {
      await deleteRoutingRule(rule.id)
      success('Regla eliminada')
      if (editingRuleId === rule.id) {
        setEditingRuleId(null)
        setRuleForm(RULE_DEFAULTS)
      }
      await loadAll()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [editingRuleId, loadAll, success, toastError])

  const handleEditRuntimeEntry = useCallback((module: RuntimeConfigModule, entry: RuntimeConfigEntry) => {
    setEditingRuntimeEntry({
      module: module.module,
      key: entry.key,
      value_kind: entry.value_kind,
    })
    setRuntimeForm(runtimeEntryToForm(entry))
    setRuntimeModuleFilter(module.module)
  }, [])

  const handleCancelRuntimeEntry = useCallback(() => {
    setEditingRuntimeEntry(null)
    setRuntimeForm({ label: '', value_text: '', value_list_text: '' })
  }, [])

  const handleSaveRuntimeEntry = useCallback(async () => {
    if (!editingRuntimeEntry) return
    const label = runtimeForm.label.trim() || null
    const isList = editingRuntimeEntry.value_kind === 'list'
    const payload = {
      label,
      value_text: isList ? null : runtimeForm.value_text.trim() || null,
      value_list: isList ? parseRuntimeList(runtimeForm.value_list_text) : [],
    }
    try {
      setSavingRuntimeEntry(true)
      await upsertRuntimeConfigEntry(editingRuntimeEntry.module, editingRuntimeEntry.key, payload)
      success('Configuracion runtime guardada')
      setEditingRuntimeEntry(null)
      setRuntimeForm({ label: '', value_text: '', value_list_text: '' })
      await loadRuntimeConfig()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSavingRuntimeEntry(false)
    }
  }, [editingRuntimeEntry, loadRuntimeConfig, runtimeForm.label, runtimeForm.value_list_text, runtimeForm.value_text, success, toastError])

  const handleDeleteRuntimeEntry = useCallback(async (module: string, key: string) => {
    if (!window.confirm(`Â¿Eliminar parametro ${module}.${key}?`)) return
    try {
      await deleteRuntimeConfigEntry(module, key)
      success('Parametro eliminado')
      if (editingRuntimeEntry?.module === module && editingRuntimeEntry?.key === key) {
        handleCancelRuntimeEntry()
      }
      await loadRuntimeConfig()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    }
  }, [editingRuntimeEntry, handleCancelRuntimeEntry, loadRuntimeConfig, success, toastError])

  const handleResetRuntimeModule = useCallback(async (module: string) => {
    if (!window.confirm(`Â¿Restablecer el modulo runtime ${module}? Se perderan los valores editados.`)) return
    try {
      setSavingRuntimeEntry(true)
      await resetRuntimeConfigModule(module)
      success(`Modulo ${module} restablecido`)
      if (editingRuntimeEntry?.module === module) {
        handleCancelRuntimeEntry()
      }
      await loadRuntimeConfig()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSavingRuntimeEntry(false)
    }
  }, [editingRuntimeEntry, handleCancelRuntimeEntry, loadRuntimeConfig, success, toastError])

  useEffect(() => {
    void loadAll(scopeFilter)
  }, [loadAll, scopeFilter])

  useEffect(() => {
    void loadVocab(unassignedOnly)
  }, [loadVocab, unassignedOnly])

  useEffect(() => {
    void loadRuntimeConfig()
  }, [loadRuntimeConfig])

  useEffect(() => {
    void loadOverview(previewForm.tenant_id)
  }, [loadOverview, previewForm.tenant_id])

  useEffect(() => {
    let cancelled = false
    const tenantId = previewForm.scope_kind === 'tenant' ? previewForm.tenant_id.trim() : ''
    if (!tenantId) {
      setPreviewDocuments([])
      return
    }
    void (async () => {
      try {
        setDocumentsLoading(true)
        const items = await listRoutingPreviewDocuments(tenantId, documentQuery)
        if (!cancelled) {
          setPreviewDocuments(items)
        }
      } catch (err: any) {
        if (!cancelled) {
          toastError(getErrorMessage(err))
          setPreviewDocuments([])
        }
      } finally {
        if (!cancelled) {
          setDocumentsLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [documentQuery, previewForm.scope_kind, previewForm.tenant_id, toastError])

  const systemRules = useMemo(() => rules.filter((rule) => rule.scope_kind === 'system').length, [rules])
  const sectorRules = useMemo(() => rules.filter((rule) => rule.scope_kind === 'sector').length, [rules])
  const tenantRules = useMemo(() => rules.filter((rule) => rule.scope_kind === 'tenant').length, [rules])
  const filteredCompanies = useMemo(() => {
    const q = companyQuery.trim().toLowerCase()
    const base = q
      ? companies.filter((company) =>
          [company.name, company.slug, company.id].some((value) =>
            String(value || '')
              .toLowerCase()
              .includes(q)
          )
        )
      : companies
    return base.slice(0, 8)
  }, [companies, companyQuery])
  const selectedCompany = useMemo(
    () => companies.find((company) => company.id === previewForm.tenant_id) || null,
    [companies, previewForm.tenant_id]
  )
  const selectedTenantLabel = useMemo(() => {
    if (overview?.tenant_name) return overview.tenant_name
    const tenantId = previewForm.tenant_id.trim()
    return tenantId || 'Sin tenant seleccionado'
  }, [overview?.tenant_name, previewForm.tenant_id])
  const runtimeModuleCount = runtimeConfig.modules.length
  const hasTenantOverview = Boolean(previewForm.tenant_id.trim())
  const filteredRuntimeModules = useMemo(() => {
    const q = runtimeModuleFilter.trim().toLowerCase()
    if (!q) return runtimeConfig.modules
    return runtimeConfig.modules.filter((module) =>
      [module.module, module.title, module.description || ''].some((value) =>
        String(value).toLowerCase().includes(q)
      )
    )
  }, [runtimeConfig.modules, runtimeModuleFilter])

  const onSubmitProfile = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      setSavingProfile(true)
      const payload = buildProfilePayload(profileForm)
      if (editingProfileCode) {
        await updateRoutingProfile(editingProfileCode, payload)
        success('Perfil de routing actualizado')
      } else {
        await createRoutingProfile(payload)
        success('Perfil de routing creado')
      }
      setProfileForm(PROFILE_DEFAULTS)
      setEditingProfileCode(null)
      await loadAll()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSavingProfile(false)
    }
  }

  const onSubmitRule = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      setSavingRule(true)
      const payload = buildRulePayload(ruleForm)
      if (editingRuleId) {
        await updateRoutingRule(editingRuleId, payload)
        success('Regla de routing actualizada')
      } else {
        await createRoutingRule(payload)
        success('Regla de routing creada')
      }
      setRuleForm(RULE_DEFAULTS)
      setEditingRuleId(null)
      await loadAll()
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSavingRule(false)
    }
  }

  const onSubmitPreview = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      setPreviewing(true)
      const payload = buildPreviewPayload(previewForm)
      const result = await previewRouting(payload)
      setPreviewResult(result)
      success('Preview de routing actualizado')
    } catch (err: any) {
      setPreviewResult(null)
      toastError(getErrorMessage(err))
    } finally {
      setPreviewing(false)
    }
  }

  const applyPreviewPreset = (preset: PreviewPreset) => {
    setPreviewForm((prev) => ({
      ...prev,
      document_id: '',
      ...preset.patch,
    }))
    setPreviewResult(null)
  }

  const selectPreviewTenant = (company: AdminCompanyOption) => {
    setPreviewForm((prev) => ({
      ...prev,
      scope_kind: 'tenant',
      tenant_id: company.id,
      document_id: '',
    }))
    setCompanyQuery(company.name)
    setDocumentQuery('')
    setPreviewDocuments([])
    setPreviewResult(null)
  }

  const selectPreviewDocument = (doc: RoutingPreviewDocument) => {
    setPreviewForm((prev) => ({
      ...prev,
      scope_kind: 'tenant',
      tenant_id: doc.tenant_id,
      document_id: doc.id,
    }))
    setPreviewResult(null)
  }

  return (
    <div className={`admin-container routing-admin routing-admin--${mainTab}`}>
      <div className="admin-header-bar">
        <div>
          <h1 className="admin-title">Routing documental</h1>
          <p className="admin-subtitle">
          Administra perfiles y reglas del importador desde base de datos. La precedencia operativa es tenant, luego sector y por último sistema.
        </p>
        </div>
        <button type="button" className="admin-refresh" onClick={() => void loadAll(scopeFilter)} disabled={loading}>
          {loading ? 'Recargando...' : 'Recargar'}
        </button>
      </div>

      <section className="routing-hero">
        <div className="routing-hero__copy">
          <div className="routing-kicker">Consola de routing y runtime</div>
          <h2>Configura, prueba y supervisa el importador sin cambiar de pantalla.</h2>
          <p>
            Selecciona un tenant para ver su estado real, usa el preview para validar reglas antes de guardar y edita el runtime solo cuando necesites tocar el motor.
          </p>
        </div>

        <div className="routing-hero__facts">
          <div className="routing-hero-fact">
            <span>Tenant</span>
            <strong>{selectedTenantLabel}</strong>
          </div>
          <div className="routing-hero-fact">
            <span>Runtime</span>
            <strong>{runtimeModuleCount} módulos</strong>
          </div>
          <div className="routing-hero-fact">
            <span>Routing</span>
            <strong>{profiles.length} perfiles · {rules.length} reglas</strong>
          </div>
          <div className="routing-hero-fact">
            <span>Preview</span>
            <strong>{hasTenantOverview ? 'con tenant' : 'sin tenant seleccionado'}</strong>
          </div>
        </div>
      </section>

      <nav className="routing-section-nav" aria-label="Navegación de secciones">
        <a href="#estado-runtime">Estado</a>
        <a href="#preview">Preview</a>
        <a href="#perfiles">Perfiles</a>
        <a href="#reglas">Reglas</a>
        <a href="#vocabulario">Vocabulario</a>
      </nav>

      <div className="routing-stats">
        <StatCard label="Perfiles" value={String(profiles.length)} helper="Comportamientos reutilizables" />
        <StatCard label="Reglas sistema" value={String(systemRules)} helper="Base global" />
        <StatCard label="Reglas sector" value={String(sectorRules)} helper="Especialización por sector" />
        <StatCard label="Reglas tenant" value={String(tenantRules)} helper="Overrides específicos" />
      </div>

      <div className="routing-mode-tabs" role="tablist" aria-label="Secciones de routing">
        {([
          ['estado', 'Estado'],
          ['preview', 'Preview'],
          ['routing', 'Routing'],
          ['runtime', 'Runtime'],
          ['vocabulario', 'Vocabulario'],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={mainTab === key}
            className={`routing-mode-tab ${mainTab === key ? 'routing-mode-tab--active' : ''}`}
            onClick={() => setMainTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {loading && <div className="mb-4 text-sm text-slate-500">Cargando configuración…</div>}

      <section id="estado-runtime" className="mb-6 grid gap-6 xl:grid-cols-2" style={{ scrollMarginTop: '1rem' }}>
        <div className="routing-shell routing-state-panel rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Estado del importador</h2>
              <p className="text-sm text-slate-500">
                Vista consolidada del tenant seleccionado, batches recientes, cola de reaplicaciÃ³n y seÃ±ales de aprendizaje.
              </p>
            </div>
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() => void loadOverview(previewForm.tenant_id)}
              disabled={overviewLoading}
            >
              {overviewLoading ? 'Actualizando...' : 'Recargar estado'}
            </button>
          </div>

          {!previewForm.tenant_id && (
            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
              Selecciona un tenant en el preview para ver su estado operativo.
            </div>
          )}

          {overview && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-sm font-semibold text-slate-900">{overview.tenant_name || overview.tenant_id}</div>
                <div className="text-xs text-slate-500">{overview.tenant_id}</div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <StatCard label="Total" value={String(overview.dashboard.total)} helper="Documentos del tenant" />
                <StatCard label="Pendientes" value={String(overview.dashboard.pendientes)} helper="Procesando o en cola" />
                <StatCard label="Revisión" value={String(overview.dashboard.en_revision)} helper="Requieren atención" />
                <StatCard label="Confirmados" value={String(overview.dashboard.confirmados)} helper="Procesados correctamente" />
                <StatCard label="Fallidos" value={String(overview.dashboard.fallidos)} helper="Errores detectados" />
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-slate-900">Batches recientes</h3>
                    <span className="text-xs text-slate-500">{overview.recent_batches.length} items</span>
                  </div>
                  <div className="space-y-2">
                    {overview.recent_batches.map((batch) => (
                      <div key={batch.id} className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-mono text-xs text-slate-700">{batch.id}</span>
                          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">{batch.estado}</span>
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {batch.confirmed_items}/{batch.total_items} confirmados | {batch.progress_pct}% | actualizaciÃ³n {new Date(batch.updated_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                    {overview.recent_batches.length === 0 && (
                      <div className="text-sm text-slate-500">No hay batches recientes.</div>
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-slate-900">Documentos recientes</h3>
                    <span className="text-xs text-slate-500">{overview.recent_documents.length} items</span>
                  </div>
                  <div className="space-y-2">
                    {overview.recent_documents.map((doc) => (
                      <div key={doc.id} className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-900">{doc.nombre_archivo}</span>
                          <span className="text-xs text-slate-500">{doc.estado}</span>
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {doc.tipo_documento_detectado || 'sin tipo'} | {doc.proveedor_detectado || 'sin proveedor'} | {doc.monto_total ?? '-'}
                        </div>
                      </div>
                    ))}
                    {overview.recent_documents.length === 0 && (
                      <div className="text-sm text-slate-500">No hay documentos recientes.</div>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-slate-900">Cola de re-proceso</h3>
                    <span className="text-xs text-slate-500">{overview.reprocess_queue.length} items</span>
                  </div>
                  <div className="space-y-2">
                    {overview.reprocess_queue.map((item) => (
                      <div key={item.id} className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-900">{item.nombre_archivo}</span>
                          <span className="text-xs text-slate-500">{item.estado}</span>
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          lag {item.version_lag} | snapshot {item.snapshot_learning_version} | aplicado {item.applied_learning_version}
                        </div>
                      </div>
                    ))}
                    {overview.reprocess_queue.length === 0 && (
                      <div className="text-sm text-slate-500">No hay documentos en cola de reaplicaciÃ³n.</div>
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-slate-900">Learning insights</h3>
                    <span className="text-xs text-slate-500">{overview.learning_insights.length} items</span>
                  </div>
                  <div className="space-y-2">
                    {overview.learning_insights.map((insight) => (
                      <div key={`${insight.source_doc_type}:${insight.document_type}`} className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-900">{insight.source_doc_type} → {insight.document_type}</span>
                          <span className="text-xs text-slate-500">{insight.signals_count} seÃ±ales</span>
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          sugerencia {Math.round(insight.suggested_confidence_threshold * 100)}% | media {Math.round(insight.avg_success_confidence * 100)}%
                        </div>
                      </div>
                    ))}
                    {overview.learning_insights.length === 0 && (
                      <div className="text-sm text-slate-500">No hay insights de aprendizaje disponibles.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {overviewLoading && <div className="mt-4 text-sm text-slate-500">Cargando estado operativo...</div>}
        </div>

        <div className="routing-shell routing-runtime-panel rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">ConfiguraciÃ³n runtime</h2>
              <p className="text-sm text-slate-500">
                Edita aquÃ­ la configuraciÃ³n viva del importador. Los cambios invalidan cache y quedan versionados en la base de datos.
              </p>
            </div>
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() => void loadRuntimeConfig()}
              disabled={runtimeLoading}
            >
              {runtimeLoading ? 'Recargando...' : 'Recargar runtime'}
            </button>
          </div>

          <label className="mb-4 block text-sm">
            <div className="mb-1 font-medium text-slate-700">Filtrar mÃ³dulos</div>
            <input
              className="w-full rounded border px-3 py-2"
              value={runtimeModuleFilter}
              onChange={(e) => setRuntimeModuleFilter(e.target.value)}
              placeholder="doc_categories, prompt_config, learning..."
            />
          </label>

          {runtimeLoading && <div className="text-sm text-slate-500">Cargando runtime config...</div>}
          {!runtimeLoading && filteredRuntimeModules.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
              No hay mÃ³dulos que coincidan con el filtro.
            </div>
          )}

          <div className="space-y-4">
            {filteredRuntimeModules.map((module) => (
              <div key={module.module} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-900">{module.title}</h3>
                      <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">{module.module}</span>
                    </div>
                    {module.description && <p className="mt-1 text-sm text-slate-500">{module.description}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{module.entries.length} entradas</span>
                    <button
                      type="button"
                      className="rounded border border-amber-300 px-3 py-1.5 text-xs text-amber-700 hover:bg-amber-50"
                      onClick={() => void handleResetRuntimeModule(module.module)}
                      disabled={savingRuntimeEntry || !module.entries.length}
                    >
                      Reset
                    </button>
                  </div>
                </div>

                <div className="space-y-3">
                  {module.entries.map((entry) => {
                    const isEditing = editingRuntimeEntry?.module === module.module && editingRuntimeEntry?.key === entry.key
                    return (
                      <div key={entry.id} className="rounded border border-slate-200 bg-white p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-semibold text-slate-900">{entry.key}</span>
                              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">{entry.value_kind}</span>
                            </div>
                            <div className="text-xs text-slate-500">{entry.label || 'Sin etiqueta'} | actualizado {new Date(entry.updated_at).toLocaleString()}</div>
                            <div className="mt-2 text-sm text-slate-700">{runtimeEntryValuePreview(entry)}</div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              className="text-blue-600 hover:underline"
                              onClick={() => handleEditRuntimeEntry(module, entry)}
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              className="text-red-700 hover:underline"
                              onClick={() => void handleDeleteRuntimeEntry(module.module, entry.key)}
                            >
                              Eliminar
                            </button>
                          </div>
                        </div>

                        {isEditing && (
                          <div className="mt-4 grid gap-3 rounded border border-slate-200 bg-slate-50 p-3">
                            <div className="grid gap-3 md:grid-cols-2">
                              <label className="text-sm">
                                <div className="mb-1 font-medium text-slate-700">Etiqueta</div>
                                <input
                                  className="w-full rounded border px-3 py-2"
                                  value={runtimeForm.label}
                                  onChange={(e) => setRuntimeForm((prev) => ({ ...prev, label: e.target.value }))}
                                />
                              </label>
                              <div className="text-sm">
                                <div className="mb-1 font-medium text-slate-700">Modo</div>
                                <div className="rounded border border-slate-200 bg-white px-3 py-2 text-slate-600">
                                  {editingRuntimeEntry.value_kind === 'list' ? 'Lista de valores' : 'Texto / JSON'}
                                </div>
                              </div>
                            </div>

                            {editingRuntimeEntry.value_kind === 'list' ? (
                              <label className="text-sm">
                                <div className="mb-1 font-medium text-slate-700">Valores</div>
                                <textarea
                                  className="min-h-[120px] w-full rounded border px-3 py-2 font-mono text-xs"
                                  value={runtimeForm.value_list_text}
                                  onChange={(e) => setRuntimeForm((prev) => ({ ...prev, value_list_text: e.target.value }))}
                                  placeholder="uno por linea"
                                />
                              </label>
                            ) : (
                              <label className="text-sm">
                                <div className="mb-1 font-medium text-slate-700">Valor</div>
                                <textarea
                                  className="min-h-[120px] w-full rounded border px-3 py-2 font-mono text-xs"
                                  value={runtimeForm.value_text}
                                  onChange={(e) => setRuntimeForm((prev) => ({ ...prev, value_text: e.target.value }))}
                                  placeholder='{"enabled": true}'
                                />
                              </label>
                            )}

                            <div className="flex flex-wrap gap-2">
                              <button
                                type="button"
                                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                                disabled={savingRuntimeEntry}
                                onClick={() => { void handleSaveRuntimeEntry() }}
                              >
                                {savingRuntimeEntry ? 'Guardando...' : 'Guardar cambios'}
                              </button>
                              <button
                                type="button"
                                className="rounded border border-slate-300 px-4 py-2 text-sm"
                                onClick={handleCancelRuntimeEntry}
                              >
                                Cancelar
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="preview" className="routing-preview-panel" style={{ scrollMarginTop: '1rem' }}>
        <div className="routing-preview-header">
          <div>
            <h2 className="routing-preview-title">Simulador de routing</h2>
            <p className="routing-preview-subtitle">
              Prueba un `doc_type` y algunos campos antes de guardar reglas nuevas. El resultado usa el mismo resolver del backend y muestra qué regla ganó.
            </p>
          </div>
          <button
            type="button"
            className="routing-secondary-button"
            onClick={() => {
              setPreviewForm(PREVIEW_DEFAULTS)
              setPreviewResult(null)
              setCompanyQuery('')
              setDocumentQuery('')
            }}
          >
            Resetear preview
          </button>
        </div>

        <div className="routing-preset-row">
          {PREVIEW_PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className="routing-preset-button"
              onClick={() => applyPreviewPreset(preset)}
              title={preset.description}
            >
              <span className="routing-preset-button__label">{preset.label}</span>
              <span className="routing-preset-button__desc">{preset.description}</span>
            </button>
          ))}
        </div>

        <form className="routing-preview-grid" onSubmit={(event) => { void onSubmitPreview(event) }}>
          <div className="routing-form">
            <div className="routing-preview-fields">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Scope</div>
                <select value={previewForm.scope_kind} onChange={(e) => setPreviewForm((prev) => ({ ...prev, scope_kind: e.target.value as RoutingScopeKind }))}>
                  <option value="system">system</option>
                  <option value="sector">sector</option>
                  <option value="tenant">tenant</option>
                </select>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Source doc type</div>
                <input value={previewForm.source_doc_type} onChange={(e) => setPreviewForm((prev) => ({ ...prev, source_doc_type: e.target.value.toUpperCase() }))} placeholder="INVOICE" />
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Source category opcional</div>
                <input value={previewForm.source_category} onChange={(e) => setPreviewForm((prev) => ({ ...prev, source_category: e.target.value }))} placeholder="invoice" />
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">AI confidence</div>
                <input type="number" min="0" max="1" step="0.01" value={previewForm.ai_confidence} onChange={(e) => setPreviewForm((prev) => ({ ...prev, ai_confidence: e.target.value }))} />
              </label>
            </div>

            {previewForm.scope_kind === 'sector' && (
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Sector</div>
                <input value={previewForm.sector} onChange={(e) => setPreviewForm((prev) => ({ ...prev, sector: e.target.value }))} placeholder="panaderia" />
              </label>
            )}
            {previewForm.scope_kind === 'tenant' && (
              <div className="routing-tenant-picker">
                <label className="text-sm">
                  <div className="mb-1 font-medium text-slate-700">Buscar tenant</div>
                  <input
                    value={companyQuery}
                    onChange={(e) => setCompanyQuery(e.target.value)}
                    placeholder="Busca por nombre, slug o UUID"
                  />
                </label>
                <label className="text-sm">
                  <div className="mb-1 font-medium text-slate-700">Tenant UUID</div>
                  <input value={previewForm.tenant_id} onChange={(e) => setPreviewForm((prev) => ({ ...prev, tenant_id: e.target.value }))} placeholder="00000000-0000-0000-0000-000000000000" />
                </label>
                {selectedCompany && (
                  <div className="routing-selected-company">
                    <strong>{selectedCompany.name}</strong>
                    <span>{selectedCompany.slug || selectedCompany.id}</span>
                  </div>
                )}
                <div className="routing-company-list">
                  {filteredCompanies.map((company) => (
                    <button
                      key={company.id}
                      type="button"
                      className={`routing-company-item ${previewForm.tenant_id === company.id ? 'routing-company-item--active' : ''}`}
                      onClick={() => selectPreviewTenant(company)}
                    >
                      <span className="routing-company-item__name">{company.name}</span>
                      <span className="routing-company-item__meta">{company.slug || company.id}</span>
                    </button>
                  ))}
                  {filteredCompanies.length === 0 && (
                    <div className="routing-preview-empty">No hay tenants que coincidan con la búsqueda.</div>
                  )}
                </div>
                {previewForm.tenant_id && (
                  <div className="routing-document-picker">
                    <div className="routing-document-picker__header">
                      <strong>Documentos reales recientes</strong>
                      <input
                        value={documentQuery}
                        onChange={(e) => setDocumentQuery(e.target.value)}
                        placeholder="Filtra por archivo, proveedor o tipo"
                      />
                    </div>
                    <div className="routing-document-list">
                      {previewDocuments.map((doc) => (
                        <button
                          key={doc.id}
                          type="button"
                          className={`routing-document-item ${previewForm.document_id === doc.id ? 'routing-document-item--active' : ''}`}
                          onClick={() => selectPreviewDocument(doc)}
                        >
                          <span className="routing-document-item__name">{doc.nombre_archivo}</span>
                          <span className="routing-document-item__meta">
                            {doc.tipo_documento_detectado || 'OTRO'} | {doc.proveedor_detectado || 'sin proveedor'} | {doc.monto_total ?? '-'}
                          </span>
                        </button>
                      ))}
                      {documentsLoading && <div className="routing-preview-empty">Cargando documentos...</div>}
                      {!documentsLoading && previewDocuments.length === 0 && (
                        <div className="routing-preview-empty">No hay documentos disponibles para este tenant.</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="routing-preview-fields">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Destino override</div>
                <select value={previewForm.destination_override} onChange={(e) => setPreviewForm((prev) => ({ ...prev, destination_override: e.target.value as RoutingDestination | '' }))}>
                  <option value="">Sin override</option>
                  <option value="supplier_invoice">supplier_invoice</option>
                  <option value="expense">expense</option>
                  <option value="recipe">recipe</option>
                </select>
              </label>
              <label className="routing-checkbox">
                <input type="checkbox" checked={previewForm.requires_review} onChange={(e) => setPreviewForm((prev) => ({ ...prev, requires_review: e.target.checked }))} />
                Forzar requires_review
              </label>
            </div>

            <div className="routing-preview-fields routing-preview-fields--json">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Extracted data JSON</div>
                <textarea value={previewForm.extracted_data_text} onChange={(e) => setPreviewForm((prev) => ({ ...prev, extracted_data_text: e.target.value }))} />
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Canonical fields JSON</div>
                <textarea value={previewForm.canonical_fields_text} onChange={(e) => setPreviewForm((prev) => ({ ...prev, canonical_fields_text: e.target.value }))} />
              </label>
            </div>

            {previewForm.document_id && (
              <div className="routing-selected-company">
                <strong>Preview desde documento real activo</strong>
                <span>Se usaran los datos persistidos del documento seleccionado. El JSON manual queda como referencia hasta limpiar la seleccion.</span>
              </div>
            )}

            <div className="routing-preview-actions">
              <button type="submit" disabled={previewing}>
                {previewing ? 'Resolviendo...' : 'Ejecutar preview'}
              </button>
            </div>
          </div>

          <div className="routing-preview-result">
            {previewResult ? (
              <>
                <div className="routing-preview-result__header">
                  <div>
                    <div className="routing-preview-badge">{previewResult.matched_scope}</div>
                    <h3>Perfil resuelto: {previewResult.profile_code}</h3>
                  </div>
                  <div className={`routing-confidence ${previewResult.decision.needs_human_review ? 'routing-confidence--warn' : 'routing-confidence--ok'}`}>
                    {Math.round(previewResult.decision.confidence * 100)}%
                  </div>
                </div>

                <div className="routing-preview-kv">
                  {previewResult.document_name && <div><strong>Documento:</strong> {previewResult.document_name}</div>}
                  <div><strong>Matched by:</strong> {previewResult.matched_by}</div>
                  <div><strong>Rule source:</strong> {previewResult.rule_source_kind || '-'} {previewResult.rule_source_key || ''}</div>
                  <div><strong>Sector resuelto:</strong> {previewResult.resolved_sector}</div>
                  <div><strong>Document type final:</strong> {previewResult.decision.document_type}</div>
                  <div><strong>Destino sugerido:</strong> {previewResult.decision.suggested_destination || 'manual'}</div>
                  <div><strong>Categoria detectada:</strong> {previewResult.decision.source_category || '-'}</div>
                </div>

                <div className="routing-preview-reason">
                  <strong>Razon:</strong> {previewResult.decision.reason}
                </div>

                <div className="routing-preview-flags">
                  <span className={previewResult.decision.required_fields_ok ? 'routing-flag routing-flag--ok' : 'routing-flag routing-flag--warn'}>
                    {previewResult.decision.required_fields_ok ? 'Required fields OK' : 'Required fields missing'}
                  </span>
                  <span className={previewResult.decision.needs_human_review ? 'routing-flag routing-flag--warn' : 'routing-flag routing-flag--ok'}>
                    {previewResult.decision.needs_human_review ? 'Needs human review' : 'Auto review passed'}
                  </span>
                </div>

                <div>
                  <strong>Missing fields:</strong>
                  {previewResult.decision.missing_fields.length > 0 ? (
                    <ul className="routing-preview-list">
                      {previewResult.decision.missing_fields.map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="routing-preview-empty">No faltan campos obligatorios.</div>
                  )}
                </div>
              </>
            ) : (
              <div className="routing-preview-empty">
                Ejecuta un preview para ver que perfil, regla y decision se aplicarian con la configuracion actual.
              </div>
            )}
          </div>
        </form>
      </section>

      <div className="routing-columns routing-routing-panel">
        <section id="perfiles" className="routing-panel rounded-xl border border-slate-200 bg-white p-5 shadow-sm" style={{ scrollMarginTop: '1rem' }}>
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h4 className="text-lg font-semibold text-slate-900">Perfiles base</h4>
              <p className="text-sm text-slate-500">Definen los tipos documentales y la base de decisión del routing.</p>
            </div>
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() => {
                setEditingProfileCode(null)
                setProfileForm(PROFILE_DEFAULTS)
              }}
            >
              Nuevo perfil
            </button>
          </div>

          <form className="routing-form mb-5 grid gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4" onSubmit={(event) => { void onSubmitProfile(event) }}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Código</div>
                <input className="w-full rounded border px-3 py-2" value={profileForm.code} onChange={(e) => setProfileForm((prev) => ({ ...prev, code: e.target.value }))} placeholder="supplier_invoice" />
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Document type final</div>
                <input className="w-full rounded border px-3 py-2" value={profileForm.document_type} onChange={(e) => setProfileForm((prev) => ({ ...prev, document_type: e.target.value }))} placeholder="supplier_invoice" />
              </label>
            </div>

            <label className="text-sm">
              <div className="mb-1 font-medium text-slate-700">Descripción</div>
              <input className="w-full rounded border px-3 py-2" value={profileForm.description} onChange={(e) => setProfileForm((prev) => ({ ...prev, description: e.target.value }))} placeholder="Facturas de proveedor listas para compras" />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Destino sugerido</div>
                <select className="w-full rounded border px-3 py-2" value={profileForm.suggested_destination} onChange={(e) => setProfileForm((prev) => ({ ...prev, suggested_destination: e.target.value as RoutingDestination | '' }))}>
                  <option value="">Sin destino automático</option>
                  <option value="supplier_invoice">supplier_invoice</option>
                  <option value="expense">expense</option>
                  <option value="recipe">recipe</option>
                </select>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Umbral de confianza</div>
                <input type="number" min="0" max="1" step="0.01" className="w-full rounded border px-3 py-2" value={profileForm.confidence_threshold} onChange={(e) => setProfileForm((prev) => ({ ...prev, confidence_threshold: e.target.value }))} />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Required groups</div>
                <textarea className="min-h-[110px] w-full rounded border px-3 py-2 font-mono text-xs" value={profileForm.required_groups_text} onChange={(e) => setProfileForm((prev) => ({ ...prev, required_groups_text: e.target.value }))} />
                <div className="mt-1 text-xs text-slate-500">Una línea por grupo. Usa `campo_a | campo_b` para OR.</div>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Support fields</div>
                <textarea className="min-h-[110px] w-full rounded border px-3 py-2 font-mono text-xs" value={profileForm.support_fields_text} onChange={(e) => setProfileForm((prev) => ({ ...prev, support_fields_text: e.target.value }))} />
                <div className="mt-1 text-xs text-slate-500">Separados por coma o salto de línea.</div>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Explanation fields</div>
                <textarea className="min-h-[110px] w-full rounded border px-3 py-2 font-mono text-xs" value={profileForm.explanation_fields_text} onChange={(e) => setProfileForm((prev) => ({ ...prev, explanation_fields_text: e.target.value }))} />
                <div className="mt-1 text-xs text-slate-500">Campos usados para la razón corta en UI.</div>
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={profileForm.blocked} onChange={(e) => setProfileForm((prev) => ({ ...prev, blocked: e.target.checked }))} />
                Bloqueado para guardado automático
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={profileForm.active} onChange={(e) => setProfileForm((prev) => ({ ...prev, active: e.target.checked }))} />
                Activo
              </label>
            </div>

            <div className="flex gap-3">
              <button disabled={savingProfile} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
                {savingProfile ? 'Guardando…' : editingProfileCode ? 'Actualizar perfil' : 'Crear perfil'}
              </button>
              {editingProfileCode && (
                <button
                  type="button"
                  className="rounded border border-slate-300 px-4 py-2 text-sm"
                  onClick={() => {
                    setEditingProfileCode(null)
                    setProfileForm(PROFILE_DEFAULTS)
                  }}
                >
                  Cancelar edición
                </button>
              )}
            </div>
          </form>

          <div className="overflow-x-auto">
            <table className="min-w-full border border-slate-200 text-sm">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-3 py-2 text-left">Código</th>
                  <th className="px-3 py-2 text-left">Tipo final</th>
                  <th className="px-3 py-2 text-left">Destino</th>
                  <th className="px-3 py-2 text-left">Threshold</th>
                  <th className="px-3 py-2 text-left">Estado</th>
                  <th className="px-3 py-2 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {profiles.map((profile) => (
                  <tr key={profile.id} className="border-t">
                    <td className="px-3 py-2 font-medium text-slate-900">{profile.code}</td>
                    <td className="px-3 py-2">{profile.document_type}</td>
                    <td className="px-3 py-2">{profile.suggested_destination || 'manual'}</td>
                    <td className="px-3 py-2">{profile.confidence_threshold.toFixed(2)}</td>
                    <td className="px-3 py-2">
                      {!profile.active ? 'Inactivo' : profile.blocked ? 'Bloqueado' : 'Activo'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-3">
                        <button
                          type="button"
                          className="text-blue-600 hover:underline"
                          onClick={() => {
                            setEditingProfileCode(profile.code)
                            setProfileForm(profileToForm(profile))
                          }}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="text-red-700 hover:underline"
                          onClick={() => { void handleDeleteProfile(profile) }}
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && profiles.length === 0 && (
                  <tr>
                    <td className="px-3 py-4 text-slate-500" colSpan={6}>No hay perfiles cargados.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section id="reglas" className="routing-panel rounded-xl border border-slate-200 bg-white p-5 shadow-sm" style={{ scrollMarginTop: '1rem' }}>
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h4 className="text-lg font-semibold text-slate-900">Reglas de resolución</h4>
              <p className="text-sm text-slate-500">Resuelven `doc_type` o `category` hacia un perfil concreto.</p>
            </div>
            <div className="flex gap-2">
              <select className="rounded border px-3 py-2 text-sm" value={scopeFilter} onChange={(e) => setScopeFilter(e.target.value as RoutingScopeKind | '')}>
                <option value="">Todos los scopes</option>
                <option value="system">Sistema</option>
                <option value="sector">Sector</option>
                <option value="tenant">Tenant</option>
              </select>
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                onClick={() => {
                  setEditingRuleId(null)
                  setRuleForm(RULE_DEFAULTS)
                }}
              >
                Nueva regla
              </button>
            </div>
          </div>

          <form className="routing-form mb-5 grid gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4" onSubmit={(event) => { void onSubmitRule(event) }}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Scope</div>
                <select className="w-full rounded border px-3 py-2" value={ruleForm.scope_kind} onChange={(e) => setRuleForm((prev) => ({ ...prev, scope_kind: e.target.value as RoutingScopeKind }))}>
                  <option value="system">system</option>
                  <option value="sector">sector</option>
                  <option value="tenant">tenant</option>
                </select>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Source kind</div>
                <select className="w-full rounded border px-3 py-2" value={ruleForm.source_kind} onChange={(e) => setRuleForm((prev) => ({ ...prev, source_kind: e.target.value as 'doc_type' | 'category' }))}>
                  <option value="doc_type">doc_type</option>
                  <option value="category">category</option>
                </select>
              </label>
            </div>

            {ruleForm.scope_kind === 'sector' && (
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Sector</div>
                <input className="w-full rounded border px-3 py-2" value={ruleForm.sector} onChange={(e) => setRuleForm((prev) => ({ ...prev, sector: e.target.value }))} placeholder="panaderia" />
              </label>
            )}
            {ruleForm.scope_kind === 'tenant' && (
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Tenant UUID</div>
                <input className="w-full rounded border px-3 py-2 font-mono text-xs" value={ruleForm.tenant_id} onChange={(e) => setRuleForm((prev) => ({ ...prev, tenant_id: e.target.value }))} placeholder="00000000-0000-0000-0000-000000000000" />
              </label>
            )}

            <div className="grid gap-4 md:grid-cols-3">
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Source key</div>
                <input className="w-full rounded border px-3 py-2 font-mono text-sm" value={ruleForm.source_key} onChange={(e) => setRuleForm((prev) => ({ ...prev, source_key: e.target.value.toUpperCase() }))} placeholder="INVOICE" />
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Profile code</div>
                <select className="w-full rounded border px-3 py-2" value={ruleForm.profile_code} onChange={(e) => setRuleForm((prev) => ({ ...prev, profile_code: e.target.value }))}>
                  <option value="">Selecciona un perfil</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.code}>{profile.code}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <div className="mb-1 font-medium text-slate-700">Priority</div>
                <input type="number" min="0" max="10000" className="w-full rounded border px-3 py-2" value={ruleForm.priority} onChange={(e) => setRuleForm((prev) => ({ ...prev, priority: e.target.value }))} />
              </label>
            </div>

            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={ruleForm.active} onChange={(e) => setRuleForm((prev) => ({ ...prev, active: e.target.checked }))} />
              Activa
            </label>

            <div className="flex gap-3">
              <button disabled={savingRule} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
                {savingRule ? 'Guardando…' : editingRuleId ? 'Actualizar regla' : 'Crear regla'}
              </button>
              {editingRuleId && (
                <button
                  type="button"
                  className="rounded border border-slate-300 px-4 py-2 text-sm"
                  onClick={() => {
                    setEditingRuleId(null)
                    setRuleForm(RULE_DEFAULTS)
                  }}
                >
                  Cancelar edición
                </button>
              )}
            </div>
          </form>

          <div className="overflow-x-auto">
            <table className="min-w-full border border-slate-200 text-sm">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-3 py-2 text-left">Scope</th>
                  <th className="px-3 py-2 text-left">Source</th>
                  <th className="px-3 py-2 text-left">Profile</th>
                  <th className="px-3 py-2 text-left">Priority</th>
                  <th className="px-3 py-2 text-left">Estado</th>
                  <th className="px-3 py-2 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id} className="border-t">
                    <td className="px-3 py-2">
                      <div className="font-medium text-slate-900">{rule.scope_kind}</div>
                      <div className="text-xs text-slate-500">{rule.tenant_id || rule.sector || '_system'}</div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-mono text-xs text-slate-700">{rule.source_kind}</div>
                      <div>{rule.source_key}</div>
                    </td>
                    <td className="px-3 py-2">{rule.profile_code}</td>
                    <td className="px-3 py-2">{rule.priority}</td>
                    <td className="px-3 py-2">{rule.active ? 'Activa' : 'Inactiva'}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-3">
                        <button
                          type="button"
                          className="text-blue-600 hover:underline"
                          onClick={() => {
                            setEditingRuleId(rule.id)
                            setRuleForm(ruleToForm(rule))
                          }}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="text-red-700 hover:underline"
                          onClick={() => { void handleDeleteRule(rule) }}
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && rules.length === 0 && (
                  <tr>
                    <td className="px-3 py-4 text-slate-500" colSpan={6}>No hay reglas para el filtro actual.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* ── Vocabulario ─────────────────────────────────────────── */}
      <section id="vocabulario" className="routing-panel rounded-xl border border-slate-200 bg-white p-5 shadow-sm" style={{ marginTop: '1.5rem', scrollMarginTop: '1rem' }}>
        <div className="mb-4 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h4 className="text-lg font-semibold text-slate-900">Vocabulario de columnas</h4>
            <p className="text-sm text-slate-500">Columnas detectadas automáticamente en documentos procesados. Asígnalas a campos canónicos para que el sistema las reconozca en futuros documentos.</p>
          </div>
          <button type="button" className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => { void loadVocab() }}>
            Recargar
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-4 flex gap-1 border-b border-slate-200">
          {(['candidates', 'aliases'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setVocabTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${vocabTab === tab ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
            >
              {tab === 'candidates' ? `Pendientes (${candidates.filter(c => !c.canonical_field).length})` : `Aliases (${aliases.length})`}
            </button>
          ))}
        </div>

        {vocabLoading && <div className="py-4 text-center text-sm text-slate-400">Cargando...</div>}

        {/* Columnas pendientes */}
        {!vocabLoading && vocabTab === 'candidates' && (
          <div>
            <div className="mb-3 flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                <input type="checkbox" checked={unassignedOnly} onChange={(e) => setUnassignedOnly(e.target.checked)} />
                Solo sin asignar
              </label>
              <span className="text-xs text-slate-400">{candidates.length} columnas</span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Columna (original)</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Normalizada</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Tipo doc</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-600">Visto</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Campo canónico</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => (
                    <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-xs">{c.alias}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-500">{c.alias_norm}</td>
                      <td className="px-3 py-2 text-xs text-slate-500">{c.doc_type ?? '—'}</td>
                      <td className="px-3 py-2 text-right text-xs font-semibold text-indigo-600">{c.seen_count}</td>
                      <td className="px-3 py-2">
                        {c.canonical_field ? (
                          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">{c.canonical_field}</span>
                        ) : assigningId === c.id ? (
                          <div className="flex items-center gap-1">
                            <select
                              className="rounded border px-2 py-1 text-xs"
                              value={assignValue}
                              onChange={(e) => setAssignValue(e.target.value)}
                            >
                              <option value="">— campo —</option>
                              {canonicalFields.map((f) => (
                                <option key={f.name} value={f.name}>{f.name}</option>
                              ))}
                            </select>
                            <button type="button" disabled={!assignValue} onClick={() => { void handleAssignCandidate(c.id, assignValue) }} className="rounded bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-700 disabled:opacity-40">OK</button>
                            <button type="button" onClick={() => { setAssigningId(null); setAssignValue('') }} className="rounded border px-2 py-1 text-xs text-slate-600 hover:bg-slate-100">✕</button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">Sin asignar</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          {!c.canonical_field && assigningId !== c.id && (
                            <button type="button" onClick={() => { setAssigningId(c.id); setAssignValue('') }} className="rounded border border-indigo-300 px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50">Asignar</button>
                          )}
                          <button type="button" onClick={() => { void handleDeleteCandidate(c.id, c.alias) }} className="rounded border border-red-200 px-2 py-1 text-xs text-red-500 hover:bg-red-50">Descartar</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {candidates.length === 0 && (
                    <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-400 text-sm">No hay columnas {unassignedOnly ? 'pendientes' : 'registradas'}.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Aliases de campos */}
        {!vocabLoading && vocabTab === 'aliases' && (
          <div>
            {/* Añadir alias manual */}
            <div className="mb-4 flex items-end gap-2 flex-wrap rounded-lg bg-slate-50 border border-slate-200 p-3">
              <label className="text-sm flex flex-col gap-1">
                <span className="font-medium text-slate-700">Campo canónico</span>
                <select className="rounded border px-2 py-1.5 text-sm" value={newAliasCanonical} onChange={(e) => setNewAliasCanonical(e.target.value)}>
                  <option value="">— seleccionar —</option>
                  {canonicalFields.map((f) => <option key={f.name} value={f.name}>{f.name}</option>)}
                </select>
              </label>
              <label className="text-sm flex flex-col gap-1">
                <span className="font-medium text-slate-700">Alias (nombre de columna)</span>
                <input className="rounded border px-2 py-1.5 text-sm" placeholder="ej: n° art." value={newAliasValue} onChange={(e) => setNewAliasValue(e.target.value)} />
              </label>
              <button type="button" disabled={savingAlias || !newAliasCanonical || !newAliasValue.trim()} onClick={() => { void handleCreateAlias() }} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-40">
                {savingAlias ? 'Guardando...' : 'Añadir alias'}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Campo canónico</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Alias</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Origen</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-600">Confirmaciones</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Última vez visto</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {aliases.map((a) => (
                    <tr key={a.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-xs font-semibold text-indigo-700">{a.canonical_field}</td>
                      <td className="px-3 py-2 font-mono text-xs">{a.alias}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${a.source === 'seed' ? 'bg-slate-100 text-slate-600' : a.source === 'learned' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                          {a.source}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-xs font-semibold text-slate-700">{a.confirmed_count}</td>
                      <td className="px-3 py-2 text-xs text-slate-400">{a.last_seen_at ? new Date(a.last_seen_at).toLocaleDateString() : '—'}</td>
                      <td className="px-3 py-2">
                        {a.source !== 'seed' && (
                          <button type="button" onClick={() => { void handleDeleteAlias(a.id, a.alias) }} className="rounded border border-red-200 px-2 py-1 text-xs text-red-500 hover:bg-red-50">Eliminar</button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {aliases.length === 0 && (
                    <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-400 text-sm">No hay aliases registrados.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
