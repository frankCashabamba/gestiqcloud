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
  return data
}

export async function fetchDocument(id: string): Promise<Documento> {
  const { data } = await api.get(TENANT_IMPORTADOR.documentById(id))
  return data
}

export async function confirmDocument(id: string, datos: Record<string, unknown>): Promise<Documento> {
  const { data } = await api.post(TENANT_IMPORTADOR.confirm(id), { datos_confirmados: datos })
  return data
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
  opts?: { recipe_id?: string; recipe_snapshot_id?: string; recipe_draft?: Record<string, unknown> }
): Promise<RunResult[]> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (opts?.recipe_id) form.append('recipe_id', opts.recipe_id)
  if (opts?.recipe_snapshot_id) form.append('recipe_snapshot_id', opts.recipe_snapshot_id)
  if (opts?.recipe_draft) form.append('recipe_draft', JSON.stringify(opts.recipe_draft))
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
