/**
 * Servicio de gestión de plantillas de mapeo de importación
 */

import { apiFetch } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'

export interface ImportTemplate {
    id: string
    tenant_id?: string
    name: string
    source_type: string // 'products', 'facturas', 'gastos', etc.
    mappings: Record<string, string>
    is_system: boolean
    created_at: string
    updated_at?: string
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
    const res = await apiFetch<any>(IMPORTS.mappings.create, {
        method: 'POST',
        authToken: token,
        body: JSON.stringify({
            name: data.name,
            mapping: data.mappings,
            description: '',
            file_pattern: null,
        }),
    })

    return {
        id: String(res.id),
        tenant_id: res.tenant_id ? String(res.tenant_id) : undefined,
        name: String(res.name || data.name),
        source_type: String(res.source_type || data.source_type || 'generic'),
        mappings: (res.mapping || res.mappings || {}) as Record<string, string>,
        is_system: false,
        created_at: String(res.created_at || new Date().toISOString()),
        updated_at: res.updated_at ? String(res.updated_at) : undefined,
    }
}

export async function listImportTemplates(
    sourceType?: string,
    token?: string
): Promise<ImportTemplate[]> {
    const data = await apiFetch<any[]>(IMPORTS.mappings.list, { authToken: token })
    const items = Array.isArray(data) ? data : []

    return items
        .map((item) => ({
            id: String(item.id),
            tenant_id: item.tenant_id ? String(item.tenant_id) : undefined,
            name: String(item.name || ''),
            source_type: String(item.source_type || ''),
            mappings: (item.mapping || item.mappings || {}) as Record<string, string>,
            is_system: false,
            created_at: String(item.created_at || new Date().toISOString()),
            updated_at: item.updated_at ? String(item.updated_at) : undefined,
        }))
        .filter((item) => !sourceType || !item.source_type || item.source_type === sourceType)
}

export async function getImportTemplate(
    id: string,
    token?: string
): Promise<ImportTemplate> {
    const data = await apiFetch<any[]>(IMPORTS.mappings.list, { authToken: token })
    const found = (Array.isArray(data) ? data : []).find((x) => String(x?.id) === String(id))
    if (!found) {
        throw new Error('Template no encontrado')
    }
    return {
        id: String(found.id),
        tenant_id: found.tenant_id ? String(found.tenant_id) : undefined,
        name: String(found.name || ''),
        source_type: String(found.source_type || 'generic'),
        mappings: (found.mapping || found.mappings || {}) as Record<string, string>,
        is_system: false,
        created_at: String(found.created_at || new Date().toISOString()),
        updated_at: found.updated_at ? String(found.updated_at) : undefined,
    }
}

export async function deleteImportTemplate(
    id: string,
    token?: string
): Promise<void> {
    await apiFetch<void>(`${IMPORTS.mappings.create}/${id}`, {
        method: 'DELETE',
        authToken: token,
    })
}
