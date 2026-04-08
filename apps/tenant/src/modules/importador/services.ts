import api from '../../shared/api/client'
import { TENANT_IMPORTADOR } from '@shared/endpoints'
import { IMPORTADOR_IMPORT_SESSION_KEY } from './constants'

export type Documento = {
  id: string
  nombre_archivo: string
  tipo_archivo: string
  tamanio_bytes: number
  tipo_documento_detectado?: string
  confianza_clasificacion?: number
  requiere_revision: boolean
  datos_extraidos?: Record<string, unknown>
  datos_confirmados?: Record<string, unknown>
  estado: string
  error_detalle?: string
  recipe_snapshot_id?: string
  synced_recipe_id?: string
  saved_as?: 'expense' | 'supplier_invoice' | 'products'
  saved_record_id?: string
  saved_at?: string
  llm_model?: string
  raw_ai_json?: Record<string, unknown>
  routing_decision?: DocumentRoutingDecision | null
  review_hints?: DocumentReviewHint[]
  assisted_review?: AssistedReview | null
  last_processing_reason?: string | null
  last_learning_reprocess_at?: string | null
  last_confirmation_mode?: string | null
  proveedor_detectado?: string
  ruc_detectado?: string
  monto_total?: number
  moneda?: string
  fecha_documento?: string
  usuario_id?: string
  created_at: string
  updated_at: string
  synced_sheets?: Record<string, { recipe_id?: string; recipe_name?: string; created_at?: string }>
  logs?: LogCambio[]
  version_links?: DocumentoVersionLink[]
}

export type DocumentRoutingDecision = {
  document_type: string
  confidence: number
  required_fields_ok: boolean
  missing_fields: string[]
  suggested_destination?: DocumentSaveDestination | null
  reason: string
  needs_human_review: boolean
  source_doc_type?: string | null
  source_category?: string | null
}

export type DocumentReviewHint = {
  field: string
  field_type: string
  priority: number
  is_missing: boolean
  corrected_count: number
  confirmed_count: number
  confirmed_examples: string[]
  last_confirmed_value?: string | null
  reason: string
}

export type AssistedReview = {
  mode: 'assisted_lines'
  reason: string
  message: string
  line_items_count: number
  scalar_fields_detected: number
  can_derive_total: boolean
}

let _categoryKeywords: Record<string, string[]> = {}

export type CanonicalField = {
  name: string
  field_type: string
  projection_column?: string | null
  line_item_slot?: string | null
  label?: string | null
}

let canonicalFieldsRequest: Promise<CanonicalField[]> | null = null
let _canonicalFieldsCache: CanonicalField[] | null = null
let _canonicalFieldLabelCache: Record<string, string> = {}
let _canonicalLineItemFieldNamesCache = new Set<string>()

export type LogCambio = {
  id: string
  accion: string
  detalle?: Record<string, unknown>
  usuario_id?: string
  created_at: string
}

export type DocumentoVersionLink = {
  id: string
  nombre_archivo: string
  estado: string
  hash_sha256?: string | null
  tipo_documento_detectado?: string | null
  created_at: string
  updated_at: string
  relation_direction: 'predecessor' | 'successor'
  relation_reason?: string | null
  depth: number
}

export type DashboardStats = {
  total: number
  pendientes: number
  en_revision: number
  confirmados: number
  fallidos: number
}

let dashboardRequest: Promise<DashboardStats> | null = null
let recipesRequest: Promise<Recipe[]> | null = null
let docCategoryKeywordsRequest: Promise<void> | null = null
let fileSupportRequest: Promise<FileSupportConfig> | null = null
let productSheetConfigRequest: Promise<void> | null = null
let docCategoryKeywordsLoaded = false
let productSheetConfigLoaded = false
const importBatchListRequests = new Map<string, Promise<ImportBatch[]>>()

function primeCanonicalFieldCaches(fields: CanonicalField[]): CanonicalField[] {
  _canonicalFieldsCache = fields
  _canonicalFieldLabelCache = {}
  _canonicalLineItemFieldNamesCache = new Set<string>()
  for (const field of fields) {
    const name = String(field.name || '').trim()
    if (!name) continue
    const label = String(field.label || '').trim()
    if (label) {
      _canonicalFieldLabelCache[name.toLowerCase()] = label
    }
    if (String(field.line_item_slot || '').trim()) {
      _canonicalLineItemFieldNamesCache.add(name.toLowerCase())
    }
  }
  return fields
}

export async function fetchCanonicalFields(): Promise<CanonicalField[]> {
  if (_canonicalFieldsCache) return _canonicalFieldsCache
  if (!canonicalFieldsRequest) {
    canonicalFieldsRequest = api.get(TENANT_IMPORTADOR.canonicalFields)
      .then(({ data }) => {
        const fields = Array.isArray(data) ? data as CanonicalField[] : []
        return primeCanonicalFieldCaches(fields)
      })
      .finally(() => {
        canonicalFieldsRequest = null
      })
  }
  return canonicalFieldsRequest
}

export function formatFieldLabel(key: string): string {
  const normalized = String(key || '').trim().toLowerCase()
  if (!normalized) return ''
  const backendLabel = _canonicalFieldLabelCache[normalized]
  if (backendLabel) return backendLabel
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function isLineItemFieldName(key: string): boolean {
  return _canonicalLineItemFieldNamesCache.has(String(key || '').trim().toLowerCase())
}

export type Recipe = {
  id: string
  name: string
  description?: string
  is_public: boolean
  archived: boolean
  created_by?: string
  created_at: string
  updated_at: string
}

export type RecipeDraft = {
  id: string
  recipe_id: string
  prompt_system?: string
  prompt_user?: string
  ai_model_config?: Record<string, unknown>
  updated_by?: string
  created_at: string
  updated_at: string
}

export type RecipeSnapshot = {
  id: string
  recipe_id: string
  draft_id?: string
  version_tag?: string
  content_json: Record<string, unknown>
  created_by?: string
  created_at: string
}

export function getDocumentData(doc: { datos_confirmados?: unknown; datos_extraidos?: unknown } | null): Record<string, unknown> {
  const source = doc?.datos_confirmados || doc?.datos_extraidos
  return source && typeof source === 'object' ? source as Record<string, unknown> : {}
}

function getCanonicalDocument(raw: Record<string, unknown>): Record<string, unknown> {
  const ai = raw.raw_ai_json
  if (!ai || typeof ai !== 'object') return {}
  const canonical = (ai as Record<string, unknown>).canonical_document
  return canonical && typeof canonical === 'object' ? canonical as Record<string, unknown> : {}
}

export function getDocumentValue(data: Record<string, unknown>, ...keys: string[]): unknown {
  const normalized: Record<string, unknown> = {}
  for (const [rawKey, value] of Object.entries(data || {})) {
    const key = String(rawKey || '').trim().toLowerCase()
    if (key && !(key in normalized)) normalized[key] = value
  }
  for (const rawKey of keys) {
    const key = String(rawKey || '').trim().toLowerCase()
    if (!key || !(key in normalized)) continue
    const value = normalized[key]
    if (typeof value === 'string' && !value.trim()) continue
    if (value != null) return value
  }
  return undefined
}

function parseNumberish(value: unknown): number | undefined {
  if (value == null || typeof value === 'boolean') return undefined
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined

  let raw = String(value).trim()
  if (!raw) return undefined
  raw = raw.replace(/[^0-9,.-]/g, '')
  if (!raw || raw === '-' || raw === '.' || raw === ',') return undefined

  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.lastIndexOf(',') > raw.lastIndexOf('.')
      ? raw.replace(/\./g, '').replace(',', '.')
      : raw.replace(/,/g, '')
  } else if (raw.includes(',') && !raw.includes('.')) {
    raw = raw.replace(',', '.')
  }

  const numeric = Number(raw)
  return Number.isFinite(numeric) ? numeric : undefined
}

function normalizeSyncedSheets(raw: unknown): Documento['synced_sheets'] {
  if (!raw || typeof raw !== 'object') return {}
  const source = raw as Record<string, unknown>
  const syncedSheets: NonNullable<Documento['synced_sheets']> = {}
  for (const [sheetName, value] of Object.entries(source)) {
    if (!sheetName || !value || typeof value !== 'object') continue
    const row = value as Record<string, unknown>
    const recipeId = typeof row.recipe_id === 'string' ? row.recipe_id.trim() : ''
    if (!recipeId) continue
    syncedSheets[sheetName] = {
      recipe_id: recipeId,
      recipe_name: typeof row.recipe_name === 'string' ? row.recipe_name : undefined,
      created_at: typeof row.created_at === 'string' ? row.created_at : undefined,
    }
  }
  return syncedSheets
}

function normalizeRoutingDecision(raw: unknown): DocumentRoutingDecision | null {
  if (!raw || typeof raw !== 'object') return null
  const data = raw as Record<string, unknown>
  const suggestedDestination = typeof data.suggested_destination === 'string'
    && ['recipe', 'expense', 'supplier_invoice'].includes(data.suggested_destination)
    ? data.suggested_destination as DocumentSaveDestination
    : null

  return {
    document_type: String(data.document_type ?? ''),
    confidence: Number(data.confidence ?? 0),
    required_fields_ok: Boolean(data.required_fields_ok),
    missing_fields: Array.isArray(data.missing_fields) ? data.missing_fields.map(String).filter(Boolean) : [],
    suggested_destination: suggestedDestination,
    reason: String(data.reason ?? ''),
    needs_human_review: Boolean(data.needs_human_review),
    source_doc_type: typeof data.source_doc_type === 'string' ? data.source_doc_type : null,
    source_category: typeof data.source_category === 'string' ? data.source_category : null,
  }
}

function normalizeReviewHints(raw: unknown): DocumentReviewHint[] {
  if (!Array.isArray(raw)) return []
  const hints: DocumentReviewHint[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const data = item as Record<string, unknown>
    const field = String(data.field ?? '').trim()
    if (!field) continue
    hints.push({
      field,
      field_type: String(data.field_type ?? 'text').trim() || 'text',
      priority: Math.max(1, Number(data.priority ?? 1) || 1),
      is_missing: Boolean(data.is_missing),
      corrected_count: Math.max(0, Number(data.corrected_count ?? 0) || 0),
      confirmed_count: Math.max(0, Number(data.confirmed_count ?? 0) || 0),
      confirmed_examples: Array.isArray(data.confirmed_examples)
        ? data.confirmed_examples.map(String).filter(Boolean)
        : [],
      last_confirmed_value: typeof data.last_confirmed_value === 'string' ? data.last_confirmed_value : null,
      reason: String(data.reason ?? ''),
    })
  }
  return hints.sort((a, b) => a.priority - b.priority || a.field.localeCompare(b.field))
}

function normalizeAssistedReview(raw: unknown): AssistedReview | null {
  if (!raw || typeof raw !== 'object') return null
  const data = raw as Record<string, unknown>
  if (data.mode !== 'assisted_lines') return null
  return {
    mode: 'assisted_lines',
    reason: String(data.reason ?? ''),
    message: String(data.message ?? ''),
    line_items_count: Math.max(0, Number(data.line_items_count ?? 0) || 0),
    scalar_fields_detected: Math.max(0, Number(data.scalar_fields_detected ?? 0) || 0),
    can_derive_total: Boolean(data.can_derive_total),
  }
}

function normalizeDocument(raw: unknown): Documento {
  const data = (raw || {}) as Record<string, unknown>
  const importData = getDocumentData(data as { datos_confirmados?: unknown; datos_extraidos?: unknown })
  const canonical = getCanonicalDocument(data)
  const rawAi = data.raw_ai_json && typeof data.raw_ai_json === 'object'
    ? data.raw_ai_json as Record<string, unknown>
    : {}
  const routingDecision = normalizeRoutingDecision(data.routing_decision ?? rawAi.routing)
  const reviewHints = normalizeReviewHints(data.review_hints)
  const assistedReview = normalizeAssistedReview(data.assisted_review ?? rawAi.assisted_review)
  const canonicalDocument = canonical.document && typeof canonical.document === 'object'
    ? canonical.document as Record<string, unknown>
    : {}
  const canonicalTotals = canonical.totals && typeof canonical.totals === 'object'
    ? canonical.totals as Record<string, unknown>
    : {}
  const canonicalCurrency = canonical.currency && typeof canonical.currency === 'object'
    ? canonical.currency as Record<string, unknown>
    : {}
  const inferredTotal = parseNumberish(getDocumentValue(importData, 'total_amount', 'monto_total', 'total', 'amount', 'importe', 'grand_total'))
  const inferredCurrency = getDocumentValue(importData, 'currency', 'moneda', 'divisa')
  const inferredDate = getDocumentValue(importData, 'issue_date', 'fecha', 'date', 'invoice_date', 'expense_date')
  const canonicalTotal = parseNumberish(canonicalTotals.total)
  const canonicalCurrencyCode = typeof canonicalCurrency.code === 'string' ? canonicalCurrency.code : undefined
  const canonicalIssueDate = typeof canonicalDocument.issue_date === 'string' ? canonicalDocument.issue_date : undefined

  return {
    ...(data as Documento),
    monto_total: data.monto_total != null ? Number(data.monto_total) : (inferredTotal ?? canonicalTotal),
    moneda: typeof data.moneda === 'string' && data.moneda.trim()
      ? data.moneda
      : (typeof inferredCurrency === 'string' ? inferredCurrency : canonicalCurrencyCode),
    fecha_documento: typeof data.fecha_documento === 'string' && data.fecha_documento.trim()
      ? data.fecha_documento
      : (typeof inferredDate === 'string' ? inferredDate : canonicalIssueDate),
    routing_decision: routingDecision,
    review_hints: reviewHints,
    assisted_review: assistedReview,
    last_processing_reason: typeof data.last_processing_reason === 'string' ? data.last_processing_reason : null,
    last_learning_reprocess_at: typeof data.last_learning_reprocess_at === 'string' ? data.last_learning_reprocess_at : null,
    last_confirmation_mode: typeof data.last_confirmation_mode === 'string' ? data.last_confirmation_mode : null,
    synced_sheets: normalizeSyncedSheets(data.synced_sheets),
  }
}

export async function fetchDocuments(params?: {
  estado?: string; limit?: number; offset?: number
}): Promise<Documento[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.documents, { params })
  return Array.isArray(data) ? data.map(normalizeDocument) : []
}

export async function fetchDocument(id: string): Promise<Documento> {
  const { data } = await api.get(TENANT_IMPORTADOR.documentById(id))
  return normalizeDocument(data)
}

export async function confirmDocument(id: string, datos: Record<string, unknown>): Promise<Documento> {
  const { data } = await api.post(TENANT_IMPORTADOR.confirm(id), { datos_confirmados: datos })
  return normalizeDocument(data)
}

export type SyncRecipeResult = {
  recipe_id: string
  recipe_name: string
  was_new: boolean
  total_cost: number
  ingredients_count: number
}

export type SyncRecipeSheetResult = {
  sheet_name: string
  status: 'created' | 'updated' | 'skipped' | 'error'
  recipe_id?: string
  recipe_name?: string
  was_new: boolean
  total_cost: number
  ingredients_count: number
  message?: string
}

export type SyncRecipesResult = {
  total_sheets: number
  processed_count: number
  skipped_count: number
  results: SyncRecipeSheetResult[]
}

export type DocumentSaveDestination = 'recipe' | 'expense' | 'supplier_invoice'
export type DocumentPaymentStatus = 'pending' | 'partial' | 'paid'

export type SaveDocumentPayload = {
  destination?: DocumentSaveDestination
  payment_status?: DocumentPaymentStatus
  paid_amount?: number
  pending_amount?: number
  payment_method?: string
  payment_method_id?: string
  paid_at?: string
  notes?: string
  update_stock?: boolean
  line_matches?: Array<{
    line_index: number
    product_id?: string | null
    persist_alias?: boolean
    create_new?: boolean
  }>
}

export type SaveDocumentResult = {
  target: 'recipes' | 'purchases' | 'expenses'
  destination: DocumentSaveDestination
  status: 'created' | 'updated' | 'skipped' | 'stock_updated'
  record_id?: string
  record_ids: string[]
  message?: string
}

export type ProductMatchCandidate = {
  product_id: string
  name: string
  sku?: string | null
  unit: string
  stock: number
  score: number
  reason: string
  inferred_factor: number
}

export type DocumentLineMatch = {
  line_index: number
  description: string
  quantity: number
  unit_price: number
  selected_product_id?: string | null
  selected_reason?: string | null
  inferred_factor: number
  candidates: ProductMatchCandidate[]
}

export type DocCategory =
  | 'expense'
  | 'supplier_invoice'
  | 'recipe'
  | 'daily_log'
  | 'bank'
  | 'inventory'
  | 'payroll'
  | 'other'

function mapRoutingSourceCategory(category?: string | null): DocCategory | null {
  switch (category) {
    case 'invoice':
      return 'supplier_invoice'
    case 'receipt':
      return 'expense'
    case 'recipe':
      return 'recipe'
    case 'inventory':
      return 'inventory'
    case 'bank':
      return 'bank'
    case 'payroll':
      return 'payroll'
    default:
      return null
  }
}

function mapSuggestedDestination(destination?: DocumentSaveDestination | null): DocCategory | null {
  switch (destination) {
    case 'recipe':
      return 'recipe'
    case 'expense':
      return 'expense'
    case 'supplier_invoice':
      return 'supplier_invoice'
    default:
      return null
  }
}

export function suggestSaveDestination(doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total' | 'routing_decision'>): DocumentSaveDestination {
  if (doc.routing_decision?.suggested_destination) return doc.routing_decision.suggested_destination
  const category = getDocCategory(doc, [])
  if (category === 'recipe') return 'recipe'
  if (category === 'supplier_invoice') return 'supplier_invoice'
  return 'expense'
}

/** Override the local category keyword map with server-fetched data. */
function setDocCategoryKeywords(map: Record<string, string[]>) {
  _categoryKeywords = map
}

export type FileSupportConfig = {
  accepted_extensions: string[]
  image_extensions: string[]
  type_map: Record<string, string>
}

export type ProductSheetDetectionConfig = {
  summary_names: string[]
  name_keywords: string[]
  price_keywords: string[]
  price_reject_keywords: string[]
  cost_keywords: string[]
  sku_keywords: string[]
  category_keywords: string[]
  description_keywords: string[]
  explicit_stock_keywords: string[]
  ambiguous_stock_keywords: string[]
  operational_keywords: string[]
  sheet_hint_keywords: string[]
}

let _productSheetDetection: ProductSheetDetectionConfig = {
  summary_names: [],
  name_keywords: [],
  price_keywords: [],
  price_reject_keywords: [],
  cost_keywords: [],
  sku_keywords: [],
  category_keywords: [],
  description_keywords: [],
  explicit_stock_keywords: [],
  ambiguous_stock_keywords: [],
  operational_keywords: [],
  sheet_hint_keywords: [],
}


function _matchesAny(tipo: string, keywords: string[]): boolean {
  return keywords.some(kw => tipo.includes(kw))
}

function _normalizeLoose(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function _matchesLooseKeyword(value: string, keywords: string[]): boolean {
  return keywords.some((keyword) => value === keyword || value.includes(keyword))
}

function setProductSheetDetectionConfig(config: ProductSheetDetectionConfig) {
  _productSheetDetection = config
}

export function getDocCategory(
  doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total' | 'routing_decision'>,
  _sheets: string[],
): DocCategory {
  const routedCategory = mapRoutingSourceCategory(doc.routing_decision?.source_category)
  if (routedCategory) return routedCategory
  const routedDestination = mapSuggestedDestination(doc.routing_decision?.suggested_destination)
  if (routedDestination) return routedDestination
  const tipo = String(doc.tipo_documento_detectado || '').trim().toUpperCase()
  // Keyword substring match against the DB-driven map (works for any free-form AI label)
  if (_matchesAny(tipo, _categoryKeywords.recipe    ?? [])) return 'recipe'
  if (_matchesAny(tipo, _categoryKeywords.receipt   ?? [])) return 'expense'
  if (_matchesAny(tipo, _categoryKeywords.invoice   ?? [])) return 'supplier_invoice'
  if (_matchesAny(tipo, _categoryKeywords.inventory ?? [])) return 'inventory'
  if (_matchesAny(tipo, _categoryKeywords.bank      ?? [])) return 'bank'
  if (_matchesAny(tipo, _categoryKeywords.payroll   ?? [])) return 'payroll'
  return 'other'
}

export function canSaveDocument(doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total' | 'routing_decision'>): boolean {
  const category = getDocCategory(doc, [])
  return category === 'recipe' || category === 'expense' || category === 'supplier_invoice' || category === 'daily_log'
}

export function hasConfirmedDocumentData(
  doc: Pick<Documento, 'datos_confirmados'>
): boolean {
  return Boolean(doc.datos_confirmados && Object.keys(doc.datos_confirmados).length > 0)
}

export function isDocumentSaved(
  doc: Pick<Documento, 'estado' | 'saved_as' | 'saved_at' | 'synced_recipe_id' | 'synced_sheets'>
): boolean {
  const hasDirectRecipeSync = typeof doc.synced_recipe_id === 'string' && doc.synced_recipe_id.trim().length > 0
  const hasSheetRecipeSync = Boolean(doc.synced_sheets && Object.keys(doc.synced_sheets).length > 0)
  return doc.estado === 'IMPORTED'
    || doc.saved_as != null
    || Boolean(doc.saved_at)
    || hasDirectRecipeSync
    || hasSheetRecipeSync
}

export function getDocumentDisplayStatus(
  doc: Pick<Documento, 'estado' | 'saved_as' | 'saved_at' | 'synced_recipe_id' | 'synced_sheets'>
): string {
  if (isDocumentSaved(doc)) return 'CONFIRMED'
  return doc.estado
}

export function canSaveProductsSheet(
  docCategory: DocCategory,
  sheetName: string | null,
  columnKeys: string[],
): boolean {
  if (!columnKeys.length) return false
  if (docCategory === 'bank' || docCategory === 'payroll' || docCategory === 'recipe') return false

  const normalizedSheet = _normalizeLoose(String(sheetName || ''))
  const normalizedKeys = columnKeys.map(_normalizeLoose).filter(Boolean)
  if (!normalizedKeys.length) return false

  const hasName = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.name_keywords))
  if (!hasName) return false

  const hasSheetHint = _matchesLooseKeyword(normalizedSheet, _productSheetDetection.sheet_hint_keywords)
  const hasPrice = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.price_keywords))
  const hasStock = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.explicit_stock_keywords))
  const hasCost = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.cost_keywords))
  const hasSku = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.sku_keywords))
  const hasCategory = normalizedKeys.some((key) => _matchesLooseKeyword(key, _productSheetDetection.category_keywords))

  if (docCategory === 'inventory') return hasName
  return hasSheetHint || hasPrice || hasStock || hasCost || hasSku || hasCategory
}

export async function syncRecipe(id: string, sheet_usada?: string): Promise<SyncRecipeResult> {
  const { data } = await api.post(TENANT_IMPORTADOR.syncRecipe(id), sheet_usada ? { sheet_usada } : {})
  const raw = (data || {}) as Record<string, unknown>
  return {
    recipe_id: String(raw.recipe_id ?? raw.id ?? ''),
    recipe_name: String(raw.recipe_name ?? raw.name ?? 'Receta'),
    was_new: Boolean(raw.was_new ?? raw.created ?? false),
    total_cost: Number(raw.total_cost ?? raw.costo_total ?? 0),
    ingredients_count: Number(raw.ingredients_count ?? raw.ingredientes_count ?? 0),
  }
}

export async function syncAllRecipes(id: string): Promise<SyncRecipesResult> {
  const { data } = await api.post(TENANT_IMPORTADOR.syncRecipes(id), {})
  const raw = (data || {}) as Record<string, unknown>
  const resultsRaw = Array.isArray(raw.results) ? raw.results : []
  return {
    total_sheets: Number(raw.total_sheets ?? resultsRaw.length ?? 0),
    processed_count: Number(raw.processed_count ?? 0),
    skipped_count: Number(raw.skipped_count ?? 0),
    results: resultsRaw.map((item): SyncRecipeSheetResult => {
      const row = (item || {}) as Record<string, unknown>
      const statusRaw = String(row.status ?? 'error')
      const status: SyncRecipeSheetResult['status'] =
        statusRaw === 'created' || statusRaw === 'updated' || statusRaw === 'skipped' ? statusRaw : 'error'
      return {
        sheet_name: String(row.sheet_name ?? ''),
        status,
        recipe_id: row.recipe_id ? String(row.recipe_id) : undefined,
        recipe_name: row.recipe_name ? String(row.recipe_name) : undefined,
        was_new: Boolean(row.was_new ?? false),
        total_cost: Number(row.total_cost ?? 0),
        ingredients_count: Number(row.ingredients_count ?? 0),
        message: row.message ? String(row.message) : undefined,
      }
    }),
  }
}

export async function editDocumentFields(id: string, campos: Record<string, unknown>): Promise<Documento> {
  const { data } = await api.patch(TENANT_IMPORTADOR.edit(id), { campos })
  return normalizeDocument(data)
}

export type LineItemSlot = {
  slot: string
  label: string
  field_type: string
}

let _lineItemSlotsCache: LineItemSlot[] | null = null

export async function fetchLineItemSlots(): Promise<LineItemSlot[]> {
  if (_lineItemSlotsCache) return _lineItemSlotsCache
  const { data } = await api.get(TENANT_IMPORTADOR.lineItemSlots)
  _lineItemSlotsCache = data as LineItemSlot[]
  return _lineItemSlotsCache
}

export async function rejectDocument(id: string): Promise<Documento> {
  const { data } = await api.post(TENANT_IMPORTADOR.reject(id))
  return data
}

export async function saveDocument(id: string, payload: SaveDocumentPayload): Promise<SaveDocumentResult> {
  const { data } = await api.post(TENANT_IMPORTADOR.save(id), payload)
  const raw = (data || {}) as Record<string, unknown>
  const destination = String(raw.destination || payload.destination || 'expense')
  const statusRaw = String(raw.status || 'created')
  const status: SaveDocumentResult['status'] =
    statusRaw === 'updated' || statusRaw === 'skipped' || statusRaw === 'stock_updated'
      ? statusRaw
      : 'created'

  return {
    target: raw.target === 'recipes' ? 'recipes' : raw.target === 'purchases' ? 'purchases' : 'expenses',
    destination: destination === 'recipe' || destination === 'supplier_invoice' ? destination : 'expense',
    status,
    record_id: raw.record_id ? String(raw.record_id) : undefined,
    record_ids: Array.isArray(raw.record_ids) ? raw.record_ids.map((item) => String(item)) : [],
    message: raw.message ? String(raw.message) : undefined,
  }
}

export async function fetchDocumentLineMatchCandidates(id: string): Promise<DocumentLineMatch[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.lineMatchCandidates(id))
  const lines = Array.isArray(data?.lines) ? data.lines : []
  return lines.map((raw: Record<string, unknown>) => ({
    line_index: Number(raw.line_index ?? 0),
    description: String(raw.description ?? ''),
    quantity: Number(raw.quantity ?? 0),
    unit_price: Number(raw.unit_price ?? 0),
    selected_product_id: raw.selected_product_id ? String(raw.selected_product_id) : null,
    selected_reason: raw.selected_reason ? String(raw.selected_reason) : null,
    inferred_factor: Number(raw.inferred_factor ?? 1) || 1,
    candidates: Array.isArray(raw.candidates)
      ? raw.candidates.map((candidate: Record<string, unknown>) => ({
          product_id: String(candidate.product_id ?? ''),
          name: String(candidate.name ?? ''),
          sku: candidate.sku ? String(candidate.sku) : null,
          unit: String(candidate.unit ?? 'unit'),
          stock: Number(candidate.stock ?? 0),
          score: Number(candidate.score ?? 0),
          reason: String(candidate.reason ?? 'candidate'),
          inferred_factor: Number(candidate.inferred_factor ?? 1) || 1,
        }))
      : [],
  }))
}

export async function fetchDashboard(): Promise<DashboardStats> {
  if (!dashboardRequest) {
    dashboardRequest = api.get(TENANT_IMPORTADOR.dashboard)
      .then(({ data }) => data as DashboardStats)
      .finally(() => {
        dashboardRequest = null
      })
  }
  return dashboardRequest
}

export type AsyncRunResult = {
  id: string
  batch_id: string
  batch_item_id: string
  estado: string
  nombre_archivo: string
  action?: 'CREATED' | 'REUSED' | 'REPROCESS'
  message?: string | null
}

export type ImportBatchItem = {
  id: string
  batch_id: string
  documento_id?: string
  nombre_archivo: string
  tamanio_bytes: number
  estado: string
  error_detalle?: string
  created_at: string
  updated_at: string
}

export type ImportBatch = {
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
  completed_at?: string
  items?: ImportBatchItem[]
}

function getImportadorStreamToken(): string {
  return sessionStorage.getItem('access_token_tenant')
    || sessionStorage.getItem('authToken')
    || localStorage.getItem('authToken')
    || ''
}

// --- /run-async: encola via Celery, retorna PENDING inmediatamente ---
export async function runImportAsync(
  files: File[],
  opts?: { force?: boolean; recipeSnapshotId?: string }
): Promise<AsyncRunResult[]> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  const params: Record<string, string> = {}
  if (opts?.force) params.force = 'true'
  if (opts?.recipeSnapshotId) params.recipe_snapshot_id = opts.recipeSnapshotId
  const { data } = await api.post(TENANT_IMPORTADOR.runAsync, form, {
    params,
  })
  return data
}

export async function fetchImportBatches(opts?: { active_only?: boolean; limit?: number }): Promise<ImportBatch[]> {
  const params: Record<string, string | number | boolean> = {}
  if (opts?.active_only != null) params.active_only = opts.active_only
  if (opts?.limit != null) params.limit = opts.limit
  const key = JSON.stringify(params)
  const existing = importBatchListRequests.get(key)
  if (existing) return existing

  const request = api.get(TENANT_IMPORTADOR.batches, { params })
    .then(({ data }) => Array.isArray(data) ? data as ImportBatch[] : [])
    .finally(() => {
      importBatchListRequests.delete(key)
    })

  importBatchListRequests.set(key, request)
  return request
}

export async function fetchImportBatch(id: string): Promise<ImportBatch> {
  const { data } = await api.get(TENANT_IMPORTADOR.batchById(id))
  return data
}

export function streamImportBatch(
  id: string,
  handlers: {
    onMessage: (batch: ImportBatch) => void
    onError?: () => void
  }
): () => void {
  if (typeof EventSource === 'undefined') {
    throw new Error('eventsource_not_supported')
  }

  const token = getImportadorStreamToken()
  if (!token) {
    throw new Error('missing_stream_token')
  }

  const streamUrl = `${TENANT_IMPORTADOR.batchStream(id)}?token=${encodeURIComponent(token)}`
  const source = new EventSource(streamUrl)
  let closed = false

  source.onmessage = (event) => {
    try {
      handlers.onMessage(event.data ? JSON.parse(event.data) as ImportBatch : { id } as ImportBatch)
    } catch {
      // Ignore malformed keep-alives or transient payloads.
    }
  }

  source.onerror = () => {
    if (closed) return
    closed = true
    source.close()
    handlers.onError?.()
  }

  return () => {
    closed = true
    source.close()
  }
}

// --- Recipes ---
export async function fetchRecipes(): Promise<Recipe[]> {
  if (!recipesRequest) {
    recipesRequest = api.get(TENANT_IMPORTADOR.recipes)
      .then(({ data }) => data as Recipe[])
      .finally(() => {
        recipesRequest = null
      })
  }
  return recipesRequest
}

export async function createRecipe(body: { name: string; description?: string; is_public?: boolean }): Promise<Recipe> {
  const { data } = await api.post(TENANT_IMPORTADOR.recipes, body)
  return data
}

export async function updateRecipe(id: string, body: Partial<Recipe>): Promise<Recipe> {
  const { data } = await api.patch(TENANT_IMPORTADOR.recipeById(id), body)
  return data
}

// --- Drafts ---
export async function fetchDrafts(recipeId: string): Promise<RecipeDraft[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.recipeDrafts(recipeId))
  return data
}

export async function createDraft(recipeId: string, body: { prompt_system?: string; prompt_user?: string; ai_model_config?: Record<string, unknown> }): Promise<RecipeDraft> {
  const { data } = await api.post(TENANT_IMPORTADOR.recipeDrafts(recipeId), body)
  return data
}

export async function updateDraft(draftId: string, body: Partial<RecipeDraft>): Promise<RecipeDraft> {
  const { data } = await api.patch(TENANT_IMPORTADOR.draftById(draftId), body)
  return data
}

// --- Snapshots ---
export async function fetchSnapshots(recipeId: string): Promise<RecipeSnapshot[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.recipeSnapshots(recipeId))
  return data
}

export async function createSnapshot(draftId: string, versionTag?: string): Promise<RecipeSnapshot> {
  const { data } = await api.post(TENANT_IMPORTADOR.draftSnapshot(draftId), null, {
    params: versionTag ? { version_tag: versionTag } : undefined,
  })
  return data
}

// --- Doc category keywords (from DB) ---
export async function loadDocCategoryKeywords(): Promise<void> {
  if (docCategoryKeywordsLoaded) return
  if (docCategoryKeywordsRequest) return docCategoryKeywordsRequest

  docCategoryKeywordsRequest = (async () => {
    try {
      const { data } = await api.get(TENANT_IMPORTADOR.docCategories)
      if (data && typeof data === 'object') {
        setDocCategoryKeywords(
          Object.fromEntries(
            Object.entries(data as Record<string, unknown>).map(([k, v]) => [
              k,
              Array.isArray(v) ? (v as string[]).map(s => String(s).toUpperCase()) : [],
            ])
          )
        )
        docCategoryKeywordsLoaded = true
      }
    } catch {
      // Leave category hints empty if runtime config is unavailable.
    } finally {
      docCategoryKeywordsRequest = null
    }
  })()

  return docCategoryKeywordsRequest
}

function _normalizeStringArray(raw: unknown): string[] {
  return Array.isArray(raw) ? raw.map((value) => _normalizeLoose(String(value))).filter(Boolean) : []
}

export async function loadProductSheetDetectionConfig(): Promise<void> {
  if (productSheetConfigLoaded) return
  if (productSheetConfigRequest) return productSheetConfigRequest

  productSheetConfigRequest = (async () => {
    try {
      const { data } = await api.get(TENANT_IMPORTADOR.productSheetConfig)
      setProductSheetDetectionConfig({
        summary_names: _normalizeStringArray(data?.summary_names),
        name_keywords: _normalizeStringArray(data?.name_keywords),
        price_keywords: _normalizeStringArray(data?.price_keywords),
        price_reject_keywords: _normalizeStringArray(data?.price_reject_keywords),
        cost_keywords: _normalizeStringArray(data?.cost_keywords),
        sku_keywords: _normalizeStringArray(data?.sku_keywords),
        category_keywords: _normalizeStringArray(data?.category_keywords),
        description_keywords: _normalizeStringArray(data?.description_keywords),
        explicit_stock_keywords: _normalizeStringArray(data?.explicit_stock_keywords),
        ambiguous_stock_keywords: _normalizeStringArray(data?.ambiguous_stock_keywords),
        operational_keywords: _normalizeStringArray(data?.operational_keywords),
        sheet_hint_keywords: _normalizeStringArray(data?.sheet_hint_keywords),
      })
      productSheetConfigLoaded = true
    } catch {
      // Leave product-sheet hints empty if runtime config is unavailable.
    } finally {
      productSheetConfigRequest = null
    }
  })()

  return productSheetConfigRequest
}

export async function fetchFileSupportConfig(): Promise<FileSupportConfig> {
  if (fileSupportRequest) return fileSupportRequest
  fileSupportRequest = (async () => {
    try {
      const { data } = await api.get(TENANT_IMPORTADOR.fileSupport)
      return {
        accepted_extensions: Array.isArray(data?.accepted_extensions)
          ? data.accepted_extensions.map((value: unknown) => String(value).toLowerCase())
          : [],
        image_extensions: Array.isArray(data?.image_extensions)
          ? data.image_extensions.map((value: unknown) => String(value).toLowerCase())
          : [],
        type_map: data?.type_map && typeof data.type_map === 'object'
          ? Object.fromEntries(
              Object.entries(data.type_map as Record<string, unknown>).map(([ext, fileType]) => [
                String(ext).toLowerCase(),
                String(fileType).toUpperCase(),
              ])
            )
          : {},
      }
    } finally {
      fileSupportRequest = null
    }
  })()
  return fileSupportRequest
}

// --- Daily Production Log ---
export type SaveDailyLogResult = {
  log_date: string
  inserted: number
  matched_recipes: number
  unmatched_products: string[]
}

export async function saveDailyLog(id: string, logDate?: string): Promise<SaveDailyLogResult> {
  const body = logDate ? { log_date: logDate } : {}
  const { data } = await api.post(TENANT_IMPORTADOR.saveDailyLog(id), body)
  return data as SaveDailyLogResult
}

export type SaveProductsFromDocumentPayload = {
  sheet_name?: string
  row_indexes: number[]
  category_name?: string
}

export type SaveProductsFromDocumentResult = {
  sheet_name?: string
  category_name?: string
  created: number
  updated: number
  skipped_existing: number
  skipped_invalid: number
  product_ids: string[]
  skipped_names: string[]
}

export async function saveProductsFromDocument(
  id: string,
  payload: SaveProductsFromDocumentPayload,
): Promise<SaveProductsFromDocumentResult> {
  const { data } = await api.post(TENANT_IMPORTADOR.saveProducts(id), payload)
  return data as SaveProductsFromDocumentResult
}

export async function purgeAllImportador(): Promise<{ deleted_total: number; tables: Record<string, number> }> {
  const { data } = await api.delete(TENANT_IMPORTADOR.purgeAll)
  sessionStorage.removeItem(IMPORTADOR_IMPORT_SESSION_KEY)
  return data as { deleted_total: number; tables: Record<string, number> }
}

export async function purgeFullImportador(): Promise<{ deleted_total: number; tables: Record<string, number> }> {
  const { data } = await api.delete(TENANT_IMPORTADOR.purgeFull)
  sessionStorage.removeItem(IMPORTADOR_IMPORT_SESSION_KEY)
  return data as { deleted_total: number; tables: Record<string, number> }
}

export async function fetchSaveCapabilities(): Promise<Record<string, boolean>> {
  const { data } = await api.get(TENANT_IMPORTADOR.saveCapabilities)
  return data
}

// ─── Iterative Reprocessing Types ──────────────────────────────────────────

export interface StagingLineSummary {
  pending: number
  valid: number
  imported: number
  invalid: number
  review: number
  skipped: number
  reprocess: number
}

export interface StagingLine {
  id: string
  line_number: number
  sheet_name: string | null
  raw_data: Record<string, unknown>
  normalized_data: Record<string, unknown> | null
  estado: 'PENDING' | 'VALID' | 'IMPORTED' | 'INVALID' | 'REVIEW' | 'SKIPPED' | 'REPROCESS'
  error_code: string | null
  error_detail: string | null
  campos_revision: string[] | null
  target_table: string | null
  target_id: string | null
  imported_at: string | null
  updated_at: string
}

export interface IterationScope {
  mode: 'ALL' | 'SELECTIVE'
  filter_estados: string[]
  filter_error_codes: string[]
  filter_campos: string[]
  filter_columns: string[]
  filter_lines: number[]
  filter_sheet: string | null
}

export interface IterationResult {
  iteration_id: string
  iteration_num: number
  estado: 'DONE' | 'PARTIAL' | 'NO_IMPROVEMENT' | 'ABORTED'
  improvement: boolean
  lines_attempted: number
  lines_imported: number
  lines_errored: number
  lines_skipped: number
  remaining: StagingLineSummary
  can_retry: boolean
  message: string | null
}

export interface IterationRecord {
  id: string
  iteration_num: number
  scope: string
  scope_filter: IterationScope | null
  lines_attempted: number
  lines_imported: number
  lines_errored: number
  lines_skipped: number
  improvement: boolean | null
  estado: string
  started_at: string
  completed_at: string | null
  initiated_by: string | null
}

export interface FieldStat {
  field: string
  total_lines: number
  filled: number
  empty: number
  with_error: number
  sample_values: string[]
  related_error_codes: string[]
  suggested_for_reprocess: boolean
  fill_rate: number
}

export interface FieldAnalysis {
  total_lines_analyzed: number
  fields: FieldStat[]
  suggested_reprocess_fields: string[]
  error_summary: Record<string, number>
}

export interface ReviewSession {
  id: string
  documento_id: string
  filter_estados: string[]
  filter_error_codes: string[]
  filter_campos: string[]
  filter_columns: string[]
  filter_lines: number[]
  filter_sheet: string | null
  preview_count: number
  estado: string
  created_at: string
  linked_iteration_id: string | null
}

// ─── Iterative Reprocessing API Functions ──────────────────────────────────


export async function fetchStagingSummary(documentoId: string): Promise<StagingLineSummary> {
  const { data } = await api.get(`${TENANT_IMPORTADOR.documentById(documentoId)}/staging/summary`)
  return data
}

export async function fetchStagingLines(
  documentoId: string,
  params: {
    estado?: string[]
    error_code?: string
    sheet?: string
    limit?: number
    offset?: number
  } = {}
): Promise<StagingLine[]> {
  const { data } = await api.get(`${TENANT_IMPORTADOR.documentById(documentoId)}/staging`, {
    params: {
      estado: params.estado,
      error_code: params.error_code,
      sheet: params.sheet,
      limit: params.limit,
      offset: params.offset,
    },
  })
  return data
}

export async function fetchFieldAnalysis(
  documentoId: string,
  params: { estados?: string[]; error_codes?: string[]; sheet?: string } = {}
): Promise<FieldAnalysis> {
  const { data } = await api.get(`${TENANT_IMPORTADOR.documentById(documentoId)}/staging/field-analysis`, {
    params: {
      estados: params.estados ?? ['INVALID', 'PENDING', 'REVIEW'],
      error_codes: params.error_codes,
      sheet: params.sheet,
    },
  })
  return data
}

export async function fetchIterations(documentoId: string): Promise<IterationRecord[]> {
  const { data } = await api.get(`${TENANT_IMPORTADOR.documentById(documentoId)}/iterations`)
  return data
}

export async function runIteration(
  documentoId: string,
  scope: Partial<IterationScope> = {}
): Promise<IterationResult> {
  const body: { scope: IterationScope } = {
    scope: {
      mode: scope.mode ?? 'ALL',
      filter_estados: scope.filter_estados ?? [],
      filter_error_codes: scope.filter_error_codes ?? [],
      filter_campos: scope.filter_campos ?? [],
      filter_columns: scope.filter_columns ?? [],
      filter_lines: scope.filter_lines ?? [],
      filter_sheet: scope.filter_sheet ?? null,
    },
  }
  const { data } = await api.post(`${TENANT_IMPORTADOR.documentById(documentoId)}/iterate`, body)
  return data
}

export async function createReviewSession(
  documentoId: string,
  filters: {
    filter_estados?: string[]
    filter_error_codes?: string[]
    filter_campos?: string[]
    filter_columns?: string[]
    filter_lines?: number[]
    filter_sheet?: string | null
  }
): Promise<ReviewSession> {
  const { data } = await api.post(`${TENANT_IMPORTADOR.documentById(documentoId)}/review-session`, filters)
  return data
}

export async function runReviewSession(
  documentoId: string,
  sessionId: string
): Promise<IterationResult> {
  const { data } = await api.post(
    `${TENANT_IMPORTADOR.documentById(documentoId)}/review-session/${sessionId}/run`
  )
  return data
}

export async function patchStagingLine(
  documentoId: string,
  lineId: string,
  patch: {
    estado?: 'REPROCESS' | 'REVIEW' | 'SKIPPED'
    campos_revision?: string[] | null
    normalized_data?: Record<string, unknown> | null
  }
): Promise<StagingLine> {
  const { data } = await api.patch(`${TENANT_IMPORTADOR.documentById(documentoId)}/staging/${lineId}`, patch)
  return data
}

export async function bulkPatchStagingLines(
  documentoId: string,
  lineIds: string[],
  estado: 'REPROCESS' | 'REVIEW' | 'SKIPPED',
  camposRevision?: string[]
): Promise<{ updated: number; estado: string }> {
  const { data } = await api.patch(`${TENANT_IMPORTADOR.documentById(documentoId)}/staging/bulk`, {
    line_ids: lineIds,
    estado,
    campos_revision: camposRevision ?? null,
  })
  return data
}
