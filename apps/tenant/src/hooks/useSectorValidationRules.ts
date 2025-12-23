/**
 * useSectorValidationRules
 *
 * Hook para cargar reglas de validación DINÁMICAS de un sector desde la BD.
 * Reemplaza validaciones hardcodeadas en useSectorValidation.ts
 *
 * Proporciona:
 * - Reglas por contexto (product, inventory, sale, customer)
 * - Lógica de condición JSON flexible
 * - Mensajes personalizables
 * - Nivel de severidad (error/warning)
 *
 * Usa endpoint: GET /api/v1/sectors/{code}/validations
 *
 * Uso:
 * ```tsx
 * const { rules, loading, error } = useSectorValidationRules('panaderia', 'product')
 *
 * if (loading) return <div>Cargando...</div>
 *
 * for (const rule of rules) {
 *   if (evaluateCondition(rule.condition, formData)) {
 *     errors.push({ field: rule.field, message: rule.message, level: rule.level })
 *   }
 * }
 * ```
 */

import { useEffect, useState, useCallback } from 'react'
import tenantApi from '../shared/api/client'

// ============================================================================
// INTERFACES
// ============================================================================

export interface ValidationCondition {
  [key: string]: any
  // Ejemplos:
  // { "required": true }
  // { "min_value": 0 }
  // { "max_value": 100 }
  // { "pattern": "^[A-Z]" }
  // { "custom": "myCustomValidationFunction" }
}

export interface SectorValidationRule {
  id: string
  context: 'product' | 'inventory' | 'sale' | 'customer'
  field: string
  rule_type: 'required' | 'min_value' | 'max_value' | 'pattern' | 'custom'
  message: string
  level: 'error' | 'warning'
  condition: ValidationCondition
  enabled: boolean
  order: number
}

export interface SectorValidationRulesResponse {
  ok: boolean
  code: string
  context: string | null
  validations: SectorValidationRule[]
}

interface UseSectorValidationRulesState {
  rules: SectorValidationRule[]
  loading: boolean
  error: string | null
}

// ============================================================================
// CACHE
// ============================================================================

interface CacheEntry {
  rules: SectorValidationRule[]
  timestamp: number
}

const rulesCache = new Map<string, CacheEntry>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutos

function getCacheKey(sectorCode: string, context?: string): string {
  return context ? `${sectorCode}:${context}` : sectorCode
}

// ============================================================================
// HOOK PRINCIPAL
// ============================================================================

export function useSectorValidationRules(
  sectorCode: string | null | undefined,
  context?: 'product' | 'inventory' | 'sale' | 'customer'
): UseSectorValidationRulesState {
  const [state, setState] = useState<UseSectorValidationRulesState>({
    rules: [],
    loading: false,
    error: null,
  })

  const loadRules = useCallback(async () => {
    if (!sectorCode) {
      setState({ rules: [], loading: false, error: null })
      return
    }

    const cacheKey = getCacheKey(sectorCode, context)

    // Verificar cache
    if (rulesCache.has(cacheKey)) {
      const cached = rulesCache.get(cacheKey)!
      if (Date.now() - cached.timestamp < CACHE_TTL) {
        setState({
          rules: cached.rules,
          loading: false,
          error: null,
        })
        return
      } else {
        rulesCache.delete(cacheKey)
      }
    }

    setState({ rules: [], loading: true, error: null })

    try {
      const params = context ? `?context=${context}` : ''
      const response = await tenantApi.get<SectorValidationRulesResponse>(
        `/api/v1/sectors/${sectorCode.toLowerCase()}/validations${params}`
      )

      const rules = response.data.validations || []

      // Guardar en cache con timestamp
      rulesCache.set(cacheKey, {
        rules,
        timestamp: Date.now(),
      })

      setState({
        rules,
        loading: false,
        error: null,
      })
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        `Error cargando validaciones del sector '${sectorCode}'`

      console.error('[useSectorValidationRules]', {
        sectorCode,
        context,
        error: errorMessage,
        status: err.response?.status,
      })

      setState({
        rules: [],
        loading: false,
        error: errorMessage,
      })
    }
  }, [sectorCode, context])

  useEffect(() => {
    loadRules()
  }, [loadRules])

  return state
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Evalúa si una condición de validación se cumple
 *
 * @param condition - Condición JSON
 * @param formData - Datos del formulario
 * @param fieldValue - Valor específico del campo (opcional)
 * @returns true si la condición se cumple
 */
export function evaluateValidationCondition(
  condition: ValidationCondition,
  formData: Record<string, any>,
  fieldValue?: any
): boolean {
  if (!condition) return false

  // Usar fieldValue si se proporciona, si no extraer del formData
  const value = fieldValue !== undefined ? fieldValue : formData[Object.keys(formData)[0]]

  // required: campo debe existir y no estar vacío
  if (condition.required) {
    return value === null || value === undefined || value === ''
  }

  // min_value: valor debe ser menor que mínimo
  if (condition.min_value !== undefined) {
    return value < condition.min_value
  }

  // max_value: valor debe ser mayor que máximo
  if (condition.max_value !== undefined) {
    return value > condition.max_value
  }

  // pattern: valor no coincide con regex
  if (condition.pattern) {
    try {
      const regex = new RegExp(condition.pattern)
      return !regex.test(String(value))
    } catch {
      return false
    }
  }

  // custom: implementar lógica personalizada
  if (condition.custom) {
    // Esto requeriría evaluación dinámica
    console.warn('[evaluateValidationCondition] Custom rules requieren implementación específica')
    return false
  }

  return false
}

/**
 * Obtiene el campo de una regla
 */
export function getValidationRuleField(rule: SectorValidationRule): string {
  return rule.field
}

/**
 * Obtiene el mensaje de una regla
 */
export function getValidationRuleMessage(rule: SectorValidationRule): string {
  return rule.message
}

/**
 * Obtiene el nivel de una regla
 */
export function getValidationRuleLevel(rule: SectorValidationRule): 'error' | 'warning' {
  return rule.level
}

/**
 * Filtra reglas por contexto específico
 */
export function filterRulesByContext(
  rules: SectorValidationRule[],
  context: 'product' | 'inventory' | 'sale' | 'customer'
): SectorValidationRule[] {
  return rules.filter((rule) => rule.context === context)
}

/**
 * Filtra reglas por field específico
 */
export function filterRulesByField(
  rules: SectorValidationRule[],
  field: string
): SectorValidationRule[] {
  return rules.filter((rule) => rule.field === field)
}

/**
 * Ordena reglas por prioridad (order, luego level: error antes que warning)
 */
export function sortRulesByPriority(rules: SectorValidationRule[]): SectorValidationRule[] {
  return [...rules].sort((a, b) => {
    // Primero por order
    if (a.order !== b.order) {
      return (a.order || 0) - (b.order || 0)
    }
    // Luego por level (error antes que warning)
    const levelPriority = { error: 0, warning: 1 }
    return (levelPriority[a.level] || 0) - (levelPriority[b.level] || 0)
  })
}

/**
 * Ejecuta validación para un campo específico
 *
 * @param rules - Array de reglas de validación
 * @param fieldName - Nombre del campo
 * @param fieldValue - Valor del campo
 * @param formData - Datos completos del formulario (para contexto)
 * @returns Array de errores encontrados
 */
export function executeFieldValidation(
  rules: SectorValidationRule[],
  fieldName: string,
  fieldValue: any,
  formData?: Record<string, any>
): Array<{ level: 'error' | 'warning'; message: string }> {
  const errors: Array<{ level: 'error' | 'warning'; message: string }> = []

  const fieldRules = filterRulesByField(rules, fieldName)

  for (const rule of fieldRules) {
    // Crear objeto para evaluación
    const evalData = formData ? { ...formData, [fieldName]: fieldValue } : { [fieldName]: fieldValue }

    if (evaluateValidationCondition(rule.condition, evalData, fieldValue)) {
      errors.push({
        level: rule.level,
        message: rule.message,
      })
    }
  }

  return errors
}

/**
 * Ejecuta validación para múltiples campos
 *
 * @param rules - Array de reglas de validación
 * @param formData - Datos del formulario
 * @returns Map con errores por campo
 */
export function executeFormValidation(
  rules: SectorValidationRule[],
  formData: Record<string, any>
): Map<string, Array<{ level: 'error' | 'warning'; message: string }>> {
  const errorsByField = new Map<string, Array<{ level: 'error' | 'warning'; message: string }>>()

  // Obtener campos únicos
  const fields = new Set(rules.map((r) => r.field))

  for (const field of fields) {
    const fieldValue = formData[field]
    const fieldErrors = executeFieldValidation(rules, field, fieldValue, formData)

    if (fieldErrors.length > 0) {
      errorsByField.set(field, fieldErrors)
    }
  }

  return errorsByField
}

// ============================================================================
// CACHE MANAGEMENT
// ============================================================================

export function clearSectorValidationRulesCache() {
  rulesCache.clear()
}

export function clearSectorValidationRulesCacheForCode(sectorCode: string, context?: string) {
  const cacheKey = getCacheKey(sectorCode, context)
  rulesCache.delete(cacheKey)
}

export function getSectorValidationRulesCacheSize(): number {
  return rulesCache.size
}
