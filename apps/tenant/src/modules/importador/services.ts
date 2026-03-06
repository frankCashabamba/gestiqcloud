import api from '../../shared/api/client'
import { TENANT_IMPORTADOR } from '@shared/endpoints'

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
  llm_model?: string
  raw_ai_json?: Record<string, unknown>
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
}

export type LogCambio = {
  id: string
  accion: string
  detalle?: Record<string, unknown>
  usuario_id?: string
  created_at: string
}

export type UploadResult = {
  id: string
  estado: string
  tipo_documento_detectado?: string
  confianza_clasificacion?: number
  requiere_revision: boolean
  datos_extraidos?: Record<string, unknown>
}

export type DashboardStats = {
  total: number
  pendientes: number
  en_revision: number
  confirmados: number
  fallidos: number
}

export type RunResult = {
  id: string
  estado: string
  tipo_documento_detectado?: string
  confianza_clasificacion?: number
  requiere_revision: boolean
  datos_extraidos?: Record<string, unknown>
  llm_model?: string
  recipe_used?: string
  recipe_snapshot_id?: string
  auto_recipe_created?: boolean
  auto_recipe_name?: string
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

function getDocumentData(raw: Record<string, unknown>): Record<string, unknown> {
  const confirmed = raw.datos_confirmados
  if (confirmed && typeof confirmed === 'object') return confirmed as Record<string, unknown>
  const extracted = raw.datos_extraidos
  if (extracted && typeof extracted === 'object') return extracted as Record<string, unknown>
  return {}
}

function getDocumentValue(data: Record<string, unknown>, ...keys: string[]): unknown {
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

function normalizeDocument(raw: unknown): Documento {
  const data = (raw || {}) as Record<string, unknown>
  const importData = getDocumentData(data)
  const inferredTotal = parseNumberish(getDocumentValue(importData, 'monto_total', 'total', 'amount', 'importe', 'grand_total', 'total_general'))
  const inferredCurrency = getDocumentValue(importData, 'moneda', 'currency', 'divisa')
  const inferredDate = getDocumentValue(importData, 'fecha', 'date', 'issue_date', 'invoice_date', 'expense_date')

  return {
    ...(data as Documento),
    monto_total: data.monto_total != null ? Number(data.monto_total) : inferredTotal,
    moneda: typeof data.moneda === 'string' && data.moneda.trim()
      ? data.moneda
      : (typeof inferredCurrency === 'string' ? inferredCurrency : undefined),
    fecha_documento: typeof data.fecha_documento === 'string' && data.fecha_documento.trim()
      ? data.fecha_documento
      : (typeof inferredDate === 'string' ? inferredDate : undefined),
    synced_sheets: normalizeSyncedSheets(data.synced_sheets),
  }
}

export async function uploadFiles(files: File[]): Promise<UploadResult[]> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  const { data } = await api.post(TENANT_IMPORTADOR.upload, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
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
  return data
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
  payment_method?: 'cash' | 'bank' | 'card' | 'transfer' | 'direct_debit' | 'check' | 'other'
  paid_at?: string
  notes?: string
}

export type SaveDocumentResult = {
  target: 'recipes' | 'expenses'
  destination: DocumentSaveDestination
  status: 'created' | 'updated' | 'skipped'
  record_id?: string
  record_ids: string[]
  message?: string
}

export function suggestSaveDestination(doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total'>): DocumentSaveDestination {
  const tipo = String(doc.tipo_documento_detectado || '').trim().toUpperCase()
  if (tipo === 'COSTEO') return 'recipe'
  if (tipo === 'RECIBO' || tipo === 'BOLETA' || tipo === 'TICKET') return 'expense'
  if (tipo === 'FACTURA' || tipo === 'NOTA_CREDITO' || tipo === 'ORDEN_COMPRA' || tipo === 'PRESUPUESTO') {
    return 'supplier_invoice'
  }
  if (doc.proveedor_detectado || doc.monto_total != null) return 'supplier_invoice'
  return 'expense'
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

const EXPENSE_TYPES = new Set(['TICKETDEVENTA', 'RECIBO', 'BOLETA', 'TICKET', 'RECEIPT'])
const INVOICE_TYPES = new Set(['FACTURA', 'NOTA_CREDITO', 'ORDEN_COMPRA', 'PRESUPUESTO'])
const INVENTORY_TYPES = new Set(['INVENTARIO', 'LISTA_PRECIOS', 'CATALOGO', 'CATALOGO_PRECIOS'])
const BANK_TYPES = new Set(['EXTRACTO_BANCARIO', 'MOVIMIENTOS_BANCARIOS'])

export function getDocCategory(
  doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total'>,
  sheets: string[],
): DocCategory {
  const tipo = String(doc.tipo_documento_detectado || '').trim().toUpperCase()
  // Hoja REGISTRO tiene prioridad absoluta
  if (sheets.some(s => s.toLowerCase() === 'registro')) return 'daily_log'
  if (tipo === 'COSTEO') return 'recipe'
  if (EXPENSE_TYPES.has(tipo)) return 'expense'
  if (INVOICE_TYPES.has(tipo)) return 'supplier_invoice'
  if (INVENTORY_TYPES.has(tipo)) return 'inventory'
  if (BANK_TYPES.has(tipo)) return 'bank'
  if (tipo === 'NOMINA') return 'payroll'
  // Para OTRO/vacío: si tiene proveedor o monto es una factura/gasto, si no es genérico
  if (doc.proveedor_detectado || doc.monto_total != null) return 'supplier_invoice'
  return 'other'
}

export function canSaveDocument(doc: Pick<Documento, 'tipo_documento_detectado' | 'proveedor_detectado' | 'monto_total'>): boolean {
  const tipo = String(doc.tipo_documento_detectado || '').trim().toUpperCase()
  if (!tipo) return Boolean(doc.proveedor_detectado || doc.monto_total != null)
  return !['INVENTARIO', 'LISTA_PRECIOS', 'NOMINA', 'EXTRACTO_BANCARIO', 'MOVIMIENTOS_BANCARIOS'].includes(tipo)
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
  return data
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
    statusRaw === 'updated' || statusRaw === 'skipped' ? statusRaw : 'created'

  return {
    target: raw.target === 'recipes' ? 'recipes' : 'expenses',
    destination: destination === 'recipe' || destination === 'supplier_invoice' ? destination : 'expense',
    status,
    record_id: raw.record_id ? String(raw.record_id) : undefined,
    record_ids: Array.isArray(raw.record_ids) ? raw.record_ids.map((item) => String(item)) : [],
    message: raw.message ? String(raw.message) : undefined,
  }
}

export async function fetchLogs(docId: string): Promise<LogCambio[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.logs(docId))
  return data
}

export async function fetchDashboard(): Promise<DashboardStats> {
  const { data } = await api.get(TENANT_IMPORTADOR.dashboard)
  return data
}

// --- /run (RB-01: recipe never required) ---
export async function runImport(
  files: File[],
  opts?: { recipe_id?: string; recipe_snapshot_id?: string; recipe_draft?: Record<string, unknown>; force?: boolean }
): Promise<RunResult[]> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (opts?.recipe_id) form.append('recipe_id', opts.recipe_id)
  if (opts?.recipe_snapshot_id) form.append('recipe_snapshot_id', opts.recipe_snapshot_id)
  if (opts?.recipe_draft) form.append('recipe_draft', JSON.stringify(opts.recipe_draft))
  if (opts?.force) form.append('force', 'true')
  const { data } = await api.post(TENANT_IMPORTADOR.run, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// --- Recipes ---
export async function fetchRecipes(): Promise<Recipe[]> {
  const { data } = await api.get(TENANT_IMPORTADOR.recipes)
  return data
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
