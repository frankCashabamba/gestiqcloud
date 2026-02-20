/**
 * Importable entity types.
 * Primary source: tenant_field_configs in DB. This file is a minimal fallback.
 */

import { apiFetch } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'

export type EntityType =
  | 'products'
  | 'clientes'
  | 'proveedores'
  | 'inventario'
  | 'ventas'
  | 'compras'
  | 'facturas'
  | 'gastos'
  | 'empleados'

export type ImportFieldConfig = {
  field: string
  aliases: string[]
  required: boolean
  type: 'string' | 'number' | 'date' | 'boolean' | 'email' | 'url'
  validation?: (value: any) => boolean
  transform?: (value: any) => any
  description?: string
}

export type EntityTypeConfig = {
  type: EntityType
  label: string
  icon: string
  endpoint: string
  fields: ImportFieldConfig[]
  checkDuplicates?: boolean
  duplicateKeys?: string[]
  allowedTemplates?: string[]
}

const BASE_ENDPOINT = IMPORTS.batches.base

const BASE_ENTITY_CONFIG: Record<EntityType, EntityTypeConfig> = {
  products: {
    type: 'products',
    label: 'Productos',
    icon: '📦',
    endpoint: BASE_ENDPOINT,
    checkDuplicates: true,
    duplicateKeys: ['sku', 'codigo', 'codigo_barras'],
    fields: [
      { field: 'nombre', aliases: ['nombre', 'name'], required: true, type: 'string', description: 'Product name' },
      { field: 'sku', aliases: ['sku', 'code'], required: false, type: 'string', description: 'Internal code' },
      { field: 'precio_venta', aliases: ['precio', 'price'], required: false, type: 'number', description: 'Sale price' },
    ],
  },
  clientes: {
    type: 'clientes',
    label: 'Customers',
    icon: '👥',
    endpoint: BASE_ENDPOINT,
    checkDuplicates: true,
    duplicateKeys: ['email', 'documento'],
    fields: [
      { field: 'nombre', aliases: ['nombre', 'name'], required: true, type: 'string', description: 'Customer name' },
      { field: 'documento', aliases: ['documento', 'tax_id'], required: false, type: 'string', description: 'Tax/ID' },
      { field: 'email', aliases: ['email'], required: false, type: 'email', description: 'Email' },
    ],
  },
  proveedores: {
    type: 'proveedores',
    label: 'Suppliers',
    icon: '🏭',
    endpoint: BASE_ENDPOINT,
    checkDuplicates: true,
    duplicateKeys: ['documento', 'nombre'],
    fields: [
      { field: 'nombre', aliases: ['nombre', 'name'], required: true, type: 'string', description: 'Supplier name' },
      { field: 'documento', aliases: ['documento', 'tax_id'], required: true, type: 'string', description: 'Fiscal ID' },
      { field: 'email', aliases: ['email'], required: false, type: 'email', description: 'Email' },
    ],
  },
  inventario: {
    type: 'inventario',
    label: 'Inventory',
    icon: '📊',
    endpoint: BASE_ENDPOINT,
    fields: [
      { field: 'sku', aliases: ['sku'], required: true, type: 'string', description: 'SKU' },
      { field: 'cantidad', aliases: ['cantidad', 'quantity'], required: true, type: 'number', description: 'Quantity' },
    ],
  },
  ventas: {
    type: 'ventas',
    label: 'Sales',
    icon: '🧾',
    endpoint: BASE_ENDPOINT,
    fields: [
      { field: 'fecha', aliases: ['fecha', 'date'], required: true, type: 'date', description: 'Date' },
      { field: 'total', aliases: ['total', 'amount'], required: true, type: 'number', description: 'Total amount' },
    ],
  },
  compras: {
    type: 'compras',
    label: 'Purchases',
    icon: '📑',
    endpoint: BASE_ENDPOINT,
    fields: [
      { field: 'fecha', aliases: ['fecha', 'date'], required: true, type: 'date', description: 'Date' },
      { field: 'proveedor', aliases: ['proveedor', 'supplier'], required: true, type: 'string', description: 'Supplier' },
      { field: 'total', aliases: ['total', 'amount'], required: true, type: 'number', description: 'Total amount' },
    ],
  },
  facturas: {
    type: 'facturas',
    label: 'Invoices',
    icon: '🧾',
    endpoint: BASE_ENDPOINT,
    fields: [
      { field: 'numero', aliases: ['numero', 'number'], required: true, type: 'string', description: 'Invoice number' },
      { field: 'fecha', aliases: ['fecha', 'date'], required: true, type: 'date', description: 'Issue date' },
      { field: 'total', aliases: ['total', 'amount'], required: true, type: 'number', description: 'Total amount' },
    ],
  },
  gastos: {
    type: 'gastos',
    label: 'Expenses',
    icon: '💸',
    endpoint: BASE_ENDPOINT,
    fields: [
      { field: 'fecha', aliases: ['fecha', 'date'], required: true, type: 'date', description: 'Date' },
      { field: 'concepto', aliases: ['concepto', 'concept'], required: true, type: 'string', description: 'Concept' },
      { field: 'importe', aliases: ['importe', 'amount'], required: true, type: 'number', description: 'Amount' },
    ],
  },
  empleados: {
    type: 'empleados',
    label: 'Employees',
    icon: '🧑‍💼',
    endpoint: BASE_ENDPOINT,
    checkDuplicates: true,
    duplicateKeys: ['documento', 'email'],
    fields: [
      { field: 'nombre', aliases: ['nombre', 'name'], required: true, type: 'string', description: 'Full name' },
      { field: 'documento', aliases: ['documento', 'id'], required: true, type: 'string', description: 'ID' },
      { field: 'email', aliases: ['email'], required: false, type: 'email', description: 'Email' },
    ],
  },
}

/**
 * DEPRECATED: Usar getDynamicEntityConfig() para cargar desde BD
 *
 * Fase 4 (Hardcoding Elimination): Endpoints hardcodeados será reemplazados
 * por configuración dinámica desde sector_templates.template_config
 *
 * Timeline: Q4 2025
 * Migration: /api/v1/sectors/{code}/full-config → endpoints
 */
export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = BASE_ENTITY_CONFIG

// --- Config remota ---
export type RemoteFieldConfig = {
  field: string
  aliases?: unknown
  field_type?: string | null
  validation_pattern?: string | null
  validation_rules?: Record<string, any> | null
  transform_expression?: string | null
  visible?: boolean
  required?: boolean
  ord?: number | null
  label?: string | null
  help?: string | null
}

export type FieldConfigResponse = {
  module: string
  empresa?: string
  items?: RemoteFieldConfig[]
  form_mode?: string
}

export function getEntityConfig(type: EntityType): EntityTypeConfig {
  return ENTITY_TYPES[type]
}

// Cache sencillo por empresa+tipo para no pedir la misma configuración repetidamente
type CacheKey = string
const ENTITY_CONFIG_CACHE: Map<CacheKey, { at: number; config: EntityTypeConfig }> = new Map()
const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutos

function cacheKey(type: EntityType, empresa?: string) {
  return `${empresa || 'default'}:${type}`
}

export function clearEntityConfigCache() {
  ENTITY_CONFIG_CACHE.clear()
}

function normalizeAliases(aliases?: unknown): string[] | undefined {
  if (!aliases) return undefined
  if (Array.isArray(aliases)) {
    return aliases
      .map((a) => (a ?? '').toString().trim())
      .filter(Boolean)
  }
  return undefined
}

function mapFieldType(value: string | null | undefined, fallback: ImportFieldConfig['type']) {
  if (!value) return fallback
  const v = value.toLowerCase()
  if (['number', 'integer', 'decimal', 'currency', 'percentage'].includes(v)) return 'number'
  if (v === 'boolean') return 'boolean'
  if (v === 'date' || v === 'datetime') return 'date'
  if (v === 'email') return 'email'
  if (v === 'url') return 'url'
  return fallback
}

function buildValidationFn(pattern?: string | null, fallback?: ImportFieldConfig['validation']) {
  if (!pattern) return fallback
  try {
    const regex = new RegExp(pattern)
    return (value: any) => regex.test(String(value ?? ''))
  } catch (err) {
    console.warn('No se pudo compilar validation_pattern', err)
    return fallback
  }
}

function buildTransformFn(expr?: string | null, fallback?: ImportFieldConfig['transform']) {
  if (!expr) return fallback
  try {
    const body = typeof expr === 'string' ? expr.trim() : ''
    const fn = new Function('v', body.includes('return') ? body : `return (${body});`)
    return (value: any) => fn(value)
  } catch (err) {
    console.warn('No se pudo compilar transform_expression', err)
    return fallback
  }
}

/**
 * Merge field config desde remote + sector dynamic aliases
 * Prioridad: remote.aliases > sectorDynamicAliases > base.aliases
 *
 * Fase 4: Aliases ahora pueden venir de 3 fuentes:
 * 1. Remote: custom field_configs por empresa
 * 2. Sector: aliases dinámicos en template_config
 * 3. Base: fallback hardcodeado
 *
 * @param base - Configuración base (hardcodeada)
 * @param remote - Configuración remota (DB field_configs)
 * @param sectorDynamicAliases - Aliases dinámicos del sector
 */
function mergeFieldConfig(
  base: ImportFieldConfig,
  remote?: RemoteFieldConfig,
  sectorDynamicAliases?: Record<string, string[]>
): ImportFieldConfig {
  if (!remote && !sectorDynamicAliases) return base

  // Prioridad: remote > sector > base
  const remoteAliases = normalizeAliases(remote?.aliases)
  const dynamicAliases = sectorDynamicAliases?.[base.field]

  const merged: ImportFieldConfig = {
    ...base,
    required: remote?.required ?? base.required,
    aliases: remoteAliases ?? dynamicAliases ?? base.aliases,
    type: mapFieldType(remote?.field_type, base.type),
    validation: buildValidationFn(remote?.validation_pattern, base.validation),
    transform: buildTransformFn(remote?.transform_expression, base.transform),
    description: base.description,
  }
  return merged
}

function ensureExtraFields(base: EntityTypeConfig, remoteItems: RemoteFieldConfig[]): ImportFieldConfig[] {
  const known = new Set(base.fields.map((f) => f.field))
  const extras: ImportFieldConfig[] = []
  for (const item of remoteItems) {
    if (!item?.field || known.has(item.field)) continue
    const aliases = normalizeAliases(item.aliases) ?? [item.field]
    const type = mapFieldType(item.field_type, 'string')
    extras.push({
      field: item.field,
      aliases,
      required: Boolean(item.required),
      type,
      validation: buildValidationFn(item.validation_pattern),
      transform: buildTransformFn(item.transform_expression),
      description: item.help ?? item.label ?? undefined,
    })
  }
  return extras
}

/**
 * Merge entity config desde remote + sector dynamic aliases
 *
 * Fase 4: Ahora soporta aliases dinámicos desde sector template_config
 *
 * @param base - Configuración base (hardcodeada)
 * @param remoteItems - Items remotos (DB field_configs)
 * @param sectorDynamicAliases - Aliases dinámicos del sector (de useCompanySectorFullConfig)
 */
export function mergeEntityConfig(
  base: EntityTypeConfig,
  remoteItems: RemoteFieldConfig[],
  sectorDynamicAliases?: Record<string, string[]>
): EntityTypeConfig {
  const remoteMap = new Map(remoteItems.map((r) => [r.field, r]))
  const mergedFields = base.fields.map((f) =>
    mergeFieldConfig(f, remoteMap.get(f.field), sectorDynamicAliases)
  )
  const extraFields = ensureExtraFields(base, remoteItems)
  return {
    ...base,
    fields: [...mergedFields, ...extraFields],
  }
}

/**
 * Obtiene la configuración dinámica desde backend y la fusiona con defaults locales.
 *
 * Fase 4: Ahora carga aliases dinámicos desde sector template_config
 *
 * Fuentes (en orden de prioridad):
 * 1. Remote field_configs (per empresa)
 * 2. Sector dynamic aliases (from template_config)
 * 3. Base hardcoded aliases (fallback)
 *
 * Si falla la llamada, retorna el default local.
 */
export async function getDynamicEntityConfig(
  type: EntityType,
  opts?: { empresa?: string; sectorCode?: string }
): Promise<EntityTypeConfig> {
  const key = cacheKey(type, opts?.empresa)
  const cached = ENTITY_CONFIG_CACHE.get(key)
  if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
    return cached.config
  }

  const base = getEntityConfig(type)
  try {
    const qs = new URLSearchParams({ module: type })
    if (opts?.empresa) {
      qs.set('empresa', opts.empresa)
    }
    const res = await apiFetch<FieldConfigResponse>(`/api/v1/field-config/fields?${qs.toString()}`)
    const items = res?.items ?? []

    // Intentar cargar aliases dinámicos del sector
    let sectorDynamicAliases: Record<string, string[]> | undefined
    if (opts?.sectorCode) {
      try {
        // Cargar desde sector template_config
        const encodedSector = encodeURIComponent(opts.sectorCode)
        const sectorRes = await apiFetch<{ sector?: { fields?: Record<string, any> } }>(
          `/api/v1/sectors/${encodedSector}/full-config`
        )
        sectorDynamicAliases = sectorRes?.sector?.fields?.[type]?.aliases
      } catch (sectorErr) {
        console.debug('No se cargaron aliases dinámicos del sector, usando defaults', sectorErr)
      }
    }

    if (!items.length && !sectorDynamicAliases) {
      ENTITY_CONFIG_CACHE.set(key, { at: Date.now(), config: base })
      return base
    }

    const merged = mergeEntityConfig(base, items, sectorDynamicAliases)
    ENTITY_CONFIG_CACHE.set(key, { at: Date.now(), config: merged })
    return merged
  } catch (err) {
    console.warn('Fallo carga de config dinámica, usando defaults', err)
    ENTITY_CONFIG_CACHE.set(key, { at: Date.now(), config: base })
    return base
  }
}

export function getEntityTypesForTemplate(templateSlug: string): EntityTypeConfig[] {
  return Object.values(ENTITY_TYPES).filter(
    (config) => !config.allowedTemplates || config.allowedTemplates.includes(templateSlug)
  )
}

export function findFieldByAlias(config: EntityTypeConfig, alias: string): ImportFieldConfig | undefined {
  const normalized = alias.toLowerCase().trim()
  return config.fields.find((field) =>
    field.aliases.some((a) => a.toLowerCase() === normalized)
  )
}

/**
 * Helper para cargar config con aliases dinámicos
 *
 * Fase 4: Convenience function para consumidores de EntityConfig
 *
 * @param type - Tipo de entidad (products, clientes, etc.)
 * @param sectorCode - Código del sector para cargar aliases dinámicos
 * @param empresa - Empresa para cargar field_configs específicos
 *
 * @example
 * ```typescript
 * const config = await getDynamicEntityConfigWithSector('products', 'panaderia')
 * const field = findFieldByAlias(config, 'price')
 * ```
 */
export async function getDynamicEntityConfigWithSector(
  type: EntityType,
  sectorCode?: string,
  empresa?: string
): Promise<EntityTypeConfig> {
  return getDynamicEntityConfig(type, { empresa, sectorCode })
}

/**
 * Limpia cache de configuración
 * Llamar después de que admin actualiza sector_templates
 */
export function invalidateEntityConfigCache(module?: EntityType): void {
  if (module) {
    // Limpiar solo un módulo
    const keysToDelete: string[] = []
    for (const key of ENTITY_CONFIG_CACHE.keys()) {
      if (key.includes(`:${module}`)) {
        keysToDelete.push(key)
      }
    }
    keysToDelete.forEach(key => ENTITY_CONFIG_CACHE.delete(key))
    console.log(`Cache invalidated para ${module}`)
  } else {
    // Limpiar todo
    ENTITY_CONFIG_CACHE.clear()
    console.log('Cache completamente limpiado')
  }
}

/**
 * Recarga configuración desde API
 * Opcional: polling o webhook para detectar cambios
 */
export async function reloadEntityConfig(
  type: EntityType,
  opts?: { empresa?: string }
): Promise<EntityTypeConfig> {
  invalidateEntityConfigCache(type)
  return getDynamicEntityConfig(type, opts)
}
