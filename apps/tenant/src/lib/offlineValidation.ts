/**
 * Offline Validation Utilities
 *
 * Validates that entities are properly structured for offline sync
 * and provides type safety.
 */

import { EntityType, StoredEntity } from './offlineStore'

export type ValidationError = {
  field: string
  error: string
}

export interface OfflineEntity {
  id: string
  [key: string]: any
}

// =============================================================================
// Entity Schema Definitions
// =============================================================================

const ENTITY_SCHEMAS: Record<EntityType, {
  requiredFields: string[]
  maxSize?: number // in bytes
  immutable?: boolean
}> = {
  receipt: {
    requiredFields: ['id', 'items', 'payment_method'],
    immutable: true,
    maxSize: 1024 * 100, // 100KB max per receipt
  },
  shift: {
    requiredFields: ['id', 'register_id', 'status'],
  },
  product: {
    requiredFields: ['id', 'name', 'sku'],
    maxSize: 1024 * 50,
  },
  customer: {
    requiredFields: ['id', 'name'],
    maxSize: 1024 * 30,
  },
  sale: {
    requiredFields: ['id', 'items', 'customer_id'],
    maxSize: 1024 * 100,
  },
  purchase: {
    requiredFields: ['id', 'supplier_id', 'items'],
    maxSize: 1024 * 100,
  },
  invoice: {
    requiredFields: ['id', 'lineas'],
    maxSize: 1024 * 120,
  },
  expense: {
    requiredFields: ['id', 'amount'],
    maxSize: 1024 * 80,
  },
  inventory: {
    requiredFields: ['id'],
    maxSize: 1024 * 120,
  },
}

// =============================================================================
// Validation Functions
// =============================================================================

export function validateEntity(entity: EntityType, data: any): ValidationError[] {
  const schema = ENTITY_SCHEMAS[entity]
  if (!schema) return []

  const errors: ValidationError[] = []

  // Check required fields
  for (const field of schema.requiredFields) {
    if (!data[field]) {
      errors.push({
        field,
        error: `Missing required field: ${field}`,
      })
    }
  }

  // Check size limit
  if (schema.maxSize) {
    const size = JSON.stringify(data).length
    if (size > schema.maxSize) {
      errors.push({
        field: '_size',
        error: `Entity too large: ${size} bytes (max ${schema.maxSize})`,
      })
    }
  }

  return errors
}

export function isValidOfflineEntity(entity: EntityType, data: any): boolean {
  return validateEntity(entity, data).length === 0
}

export function assertOfflineEntity(entity: EntityType, data: any): void {
  const errors = validateEntity(entity, data)
  if (errors.length > 0) {
    const errorMsg = errors.map(e => `${e.field}: ${e.error}`).join('; ')
    throw new Error(`Invalid ${entity} for offline: ${errorMsg}`)
  }
}

// =============================================================================
// Immutability Checks
// =============================================================================

export function isEntityImmutable(entity: EntityType): boolean {
  return ENTITY_SCHEMAS[entity]?.immutable ?? false
}

export function canUpdateOffline(entity: EntityType): boolean {
  return !isEntityImmutable(entity)
}

export function canDeleteOffline(entity: EntityType): boolean {
  // Most entities can be marked as deleted, not actually removed
  return true
}

// =============================================================================
// Stored Entity Validation
// =============================================================================

export function validateStoredEntity(stored: StoredEntity): ValidationError[] {
  const errors: ValidationError[] = []

  if (!stored.id) errors.push({ field: 'id', error: 'Missing ID' })
  if (!stored.entity) errors.push({ field: 'entity', error: 'Missing entity type' })
  if (!['pending', 'synced', 'conflict', 'failed'].includes(stored.syncStatus)) {
    errors.push({ field: 'syncStatus', error: 'Invalid sync status' })
  }
  if (stored.localVersion < 0) {
    errors.push({ field: 'localVersion', error: 'Local version cannot be negative' })
  }
  if (stored.remoteVersion < 0) {
    errors.push({ field: 'remoteVersion', error: 'Remote version cannot be negative' })
  }
  if (stored.lastModified <= 0) {
    errors.push({ field: 'lastModified', error: 'Invalid timestamp' })
  }

  return errors
}

// =============================================================================
// Conflict Validation
// =============================================================================

export interface ConflictMetrics {
  fieldsInConflict: string[]
  conflictScore: number // 0-1, higher = more conflict
  isMergeable: boolean
  mergeStrategy?: 'local' | 'remote' | 'merge'
}

export function analyzeConflict(local: any, remote: any, entity: EntityType): ConflictMetrics {
  const localKeys = Object.keys(local || {})
  const remoteKeys = Object.keys(remote || {})
  const allKeys = [...new Set([...localKeys, ...remoteKeys])]

  const fieldsInConflict: string[] = []
  const schema = ENTITY_SCHEMAS[entity]

  for (const key of allKeys) {
    const localValue = local[key]
    const remoteValue = remote[key]

    if (localValue !== remoteValue) {
      // If it's a required field and differs, it's a conflict
      if (schema?.requiredFields.includes(key)) {
        fieldsInConflict.push(key)
      }
    }
  }

  const conflictScore = fieldsInConflict.length / allKeys.length

  return {
    fieldsInConflict,
    conflictScore,
    isMergeable: conflictScore < 0.5, // Less than 50% of fields differ
    mergeStrategy: isEntityImmutable(entity) ? 'local' : undefined,
  }
}

// =============================================================================
// Batch Validation
// =============================================================================

export function validateBatch(entity: EntityType, items: any[]): { valid: any[]; invalid: any[] } {
  const valid: any[] = []
  const invalid: any[] = []

  for (const item of items) {
    if (isValidOfflineEntity(entity, item)) {
      valid.push(item)
    } else {
      invalid.push(item)
    }
  }

  return { valid, invalid }
}

// =============================================================================
// Type Guards
// =============================================================================

export function isEntityType(value: unknown): value is EntityType {
  const validEntities: EntityType[] = ['receipt', 'shift', 'product', 'customer', 'sale', 'purchase', 'invoice', 'expense', 'inventory']
  return validEntities.includes(value as EntityType)
}

export function assertEntityType(value: unknown): EntityType {
  if (!isEntityType(value)) {
    throw new Error(`Invalid entity type: ${value}`)
  }
  return value as EntityType
}

// =============================================================================
// Size Estimation
// =============================================================================

export function estimateStorageSize(entity: EntityType, data: any): number {
  // Very rough estimate: JSON string length
  // Real IndexedDB might compress differently
  return JSON.stringify(data).length
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// =============================================================================
// Debug Utilities
// =============================================================================

export function getEntitySchema(entity: EntityType): typeof ENTITY_SCHEMAS[EntityType] | undefined {
  return ENTITY_SCHEMAS[entity]
}

export function getAllSchemas() {
  return ENTITY_SCHEMAS
}

export function logValidationErrors(entity: EntityType, data: any) {
  const errors = validateEntity(entity, data)
  if (errors.length > 0) {
    console.group(`❌ Validation errors for ${entity}`)
    console.table(errors)
    console.groupEnd()
  } else {
    console.log(`✅ ${entity} is valid for offline`)
  }
}
