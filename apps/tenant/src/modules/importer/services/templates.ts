/**
 * Servicio de gestión de plantillas de mapeo de importación
 */

import { apiFetch } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'
import type { TemplateV2, ImportTemplateV2, SimulateTemplateRequest, SimulateTemplateResult } from '@api-types/imports'

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

import type {
    ImportTemplateV2,
    TemplateV2,
    SimulateTemplateResult,
} from '@api-types/imports'

export async function listTemplatesV2(sourceType?: string, token?: string): Promise<ImportTemplateV2[]> {
    const data = await apiFetch<any[]>(IMPORTS.templates.list, { authToken: token })
    const items = Array.isArray(data) ? data : []
    return items
        .filter(item => !sourceType || !item.source_type || item.source_type === sourceType)
        .map(item => ({
            id: String(item.id),
            tenant_id: item.tenant_id ? String(item.tenant_id) : undefined,
            name: String(item.name || ''),
            source_type: String(item.source_type || ''),
            version: item.version || 2,
            mappings: item.mappings || {},
            transforms: item.transforms || null,
            defaults: item.defaults || null,
            dedupe_keys: item.dedupe_keys || null,
            created_at: String(item.created_at || new Date().toISOString()),
        }))
}

export async function createTemplateV2(
    data: { name: string; source_type: string; mappings: TemplateV2; transforms?: Record<string, unknown>; defaults?: Record<string, unknown>; dedupe_keys?: string[] },
    token?: string,
): Promise<ImportTemplateV2> {
    return apiFetch<ImportTemplateV2>(IMPORTS.templates.create, {
        method: 'POST',
        authToken: token,
        body: JSON.stringify({ ...data, version: 2 }),
    })
}

export async function updateTemplateV2(
    id: string,
    data: Partial<{ name: string; mappings: TemplateV2; transforms?: Record<string, unknown>; defaults?: Record<string, unknown>; dedupe_keys?: string[] }>,
    token?: string,
): Promise<ImportTemplateV2> {
    return apiFetch<ImportTemplateV2>(IMPORTS.templates.update(id), {
        method: 'PUT',
        authToken: token,
        body: JSON.stringify(data),
    })
}

export async function deleteTemplateV2(id: string, token?: string): Promise<void> {
    await apiFetch<void>(IMPORTS.templates.delete(id), {
        method: 'DELETE',
        authToken: token,
    })
}

export async function simulateTemplate(
    templateId: string,
    sampleRows: Record<string, unknown>[],
    token?: string,
): Promise<SimulateTemplateResult> {
    return apiFetch<SimulateTemplateResult>(IMPORTS.templates.simulate(templateId), {
        method: 'POST',
        authToken: token,
        body: JSON.stringify({ sample_rows: sampleRows }),
    })
}

export type TemplateFieldsResponse = { source_type: string; fields: string[]; seeded?: boolean }

export async function listTemplateFields(sourceType?: string, token?: string): Promise<TemplateFieldsResponse> {
    const qs = sourceType ? `?source_type=${encodeURIComponent(sourceType)}` : ''
    const base = IMPORTS.templates.list.replace(/\/$/, '')
    const res = await apiFetch<TemplateFieldsResponse>(`${base}/fields2${qs}`, {
        authToken: token,
    })
    return {
        source_type: res.source_type,
        fields: res.fields || [],
        seeded: res.seeded,
        source_types: (res as any).source_types,
    }
}
