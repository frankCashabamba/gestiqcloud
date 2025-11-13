import api from '../../shared/api/client'

export type UiTemplateItem = { slug: string; label: string; description?: string; pro?: boolean; active?: boolean; ord?: number }

export async function listUiTemplates(): Promise<UiTemplateItem[]> {
  // Fallback estable bajo router de settings admin
  const { data } = await api.get<{ count: number; items: UiTemplateItem[] }>(`/v1/admin/field-config/ui-plantillas`)
  return (data && data.items) || []
}

export async function createUiTemplate(payload: UiTemplateItem): Promise<UiTemplateItem> {
  const { data } = await api.post<{ ok: boolean; item: UiTemplateItem }>(`/v1/sectors/ui-plantillas`, payload)
  return data.item
}

export async function updateUiTemplate(slug: string, payload: UiTemplateItem): Promise<UiTemplateItem> {
  const { data } = await api.put<{ ok: boolean; item: UiTemplateItem }>(`/v1/sectors/ui-plantillas/${encodeURIComponent(slug)}`, payload)
  return data.item
}

export async function deleteUiTemplate(slug: string): Promise<void> {
  await api.delete(`/v1/sectors/ui-plantillas/${encodeURIComponent(slug)}`)
}
