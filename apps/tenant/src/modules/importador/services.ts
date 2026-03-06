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
  return {
    ...(data as Documento),
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
