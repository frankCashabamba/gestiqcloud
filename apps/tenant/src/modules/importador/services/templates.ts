/**
 * Servicio de gestión de plantillas de mapeo de importación
 */

import api from '../../../shared/api/client'

export interface ImportTemplate {
    id: string
    tenant_id: string
    name: string
    source_type: string // 'products', 'facturas', 'gastos', etc.
    mappings: Record<string, string>
    is_system: boolean
    created_at: string
    updated_at: string
}

export interface SaveTemplateData {
    name: string
    source_type: string
    mappings: Record<string, string>
}

export async function saveImportTemplate(
    data: SaveTemplateData,
    token?: string
): Promise<ImportTemplate> {
    const { data: res } = await api.post<ImportTemplate>(`/api/v1/imports/mappings`, {
        name: data.name,
        source_type: data.source_type,
        mappings: data.mappings,
        transforms: {},
        defaults: {},
        dedupe_keys: [],
    })
    return res
}

export async function listImportTemplates(
    sourceType?: string,
    token?: string
): Promise<ImportTemplate[]> {
    const { data } = await api.get<ImportTemplate[]>(`/api/v1/imports/mappings`, { params: { source_type: sourceType } })
    return data || []
}

export async function getImportTemplate(
    id: string,
    token?: string
): Promise<ImportTemplate> {
    const { data } = await api.get<ImportTemplate>(`/api/v1/imports/mappings/${id}`)
    return data
}

export async function deleteImportTemplate(
    id: string,
    token?: string
): Promise<void> {
    await api.delete(`/api/v1/imports/mappings/${id}`)
}
