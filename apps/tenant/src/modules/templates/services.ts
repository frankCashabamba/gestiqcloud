import api from "../../services/api/client"

export interface UIConfig {
  [key: string]: any
}

export interface TemplatePackage {
  template_key: string
  version: string
  config: UIConfig
}

export interface TemplateOverlay {
  id?: string
  template_key?: string
  config: UIConfig
  active?: boolean
  created_at?: string
  updated_at?: string
}

export async function getUIConfig(): Promise<UIConfig> {
  return api.get('/api/v1/tenant/templates/ui-config').then(r => r.data)
}

export function deepMerge(base: Record<string, any>, over: Record<string, any>): Record<string, any> {
  const out = { ...base }
  for (const [k, v] of Object.entries(over)) {
    if (k in out && typeof out[k] === 'object' && typeof v === 'object' && !Array.isArray(out[k]) && !Array.isArray(v)) {
      out[k] = deepMerge(out[k], v)
    } else {
      out[k] = v
    }
  }
  return out
}

export function validateOverlay(
  config: Record<string, any>,
  limits: { max_fields?: number; max_bytes?: number; max_depth?: number } = {}
): { valid: boolean; error?: string } {
  const maxFields = limits.max_fields ?? 15
  const maxBytes = limits.max_bytes ?? 8192
  const maxDepth = limits.max_depth ?? 2

  let fieldCount = 0
  const countFields = (obj: any): void => {
    if (typeof obj === 'object' && obj !== null) {
      if (Array.isArray(obj)) {
        obj.forEach(countFields)
      } else {
        fieldCount += Object.keys(obj).length
        Object.values(obj).forEach(countFields)
      }
    }
  }

  countFields(config)

  if (fieldCount > maxFields) {
    return { valid: false, error: `overlay_fields_exceeded:${fieldCount}>${maxFields}` }
  }

  const bytes = new Blob([JSON.stringify(config)]).size
  if (bytes > maxBytes) {
    return { valid: false, error: 'overlay_bytes_exceeded' }
  }

  const getDepth = (obj: any): number => {
    if (typeof obj !== 'object' || obj === null) return 0
    if (Array.isArray(obj)) {
      return obj.length === 0 ? 1 : 1 + Math.max(...obj.map(getDepth))
    }
    const keys = Object.keys(obj)
    return keys.length === 0 ? 1 : 1 + Math.max(...keys.map(k => getDepth(obj[k])))
  }

  if (getDepth(config) > maxDepth) {
    return { valid: false, error: 'overlay_depth_exceeded' }
  }

  return { valid: true }
}
