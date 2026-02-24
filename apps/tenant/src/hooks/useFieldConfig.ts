import React from 'react'

export type FieldCfg = {
  field: string
  visible?: boolean
  required?: boolean
  ord?: number | null
  label?: string | null
  help?: string | null
  field_type?: string | null
  type?: string | null
  options?: string[] | null
  validation_pattern?: string | null
}

/**
 * Merge base field definitions with remote overrides from field-config API.
 * Fields with visible=false in overrides are removed.
 * New fields from overrides are added.
 * Result is sorted by ord.
 */
export function mergeFieldConfig(base: FieldCfg[], overrides: FieldCfg[]): FieldCfg[] {
  const map = new Map(base.map((cfg) => [cfg.field, cfg]))
  for (const cfg of overrides) {
    if (cfg.visible === false) {
      map.delete(cfg.field)
      continue
    }
    const prev = map.get(cfg.field) || {}
    map.set(cfg.field, { ...prev, ...cfg })
  }
  return Array.from(map.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
}

/**
 * Get the effective field type. Supports both `type` (legacy) and `field_type` (from API).
 */
export function getFieldType(f: FieldCfg): string {
  return f.type || f.field_type || 'text'
}

/**
 * Render a form field dynamically based on its FieldCfg configuration.
 * Supports: text, number, date, boolean, select, textarea, email.
 *
 * @param f - Field configuration
 * @param value - Current field value
 * @param onChange - Callback when value changes. Receives (fieldName, newValue).
 */
export function renderDynamicField(
  f: FieldCfg,
  value: unknown,
  onChange: (field: string, value: unknown) => void,
): React.ReactNode {
  const fieldType = getFieldType(f)
  const strValue = value != null ? String(value) : ''
  const inputClass = 'border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
  const pattern = f.validation_pattern || undefined

  switch (fieldType) {
    case 'number':
      return React.createElement('input', {
        type: 'number',
        step: '0.01',
        value: value ?? '',
        onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(f.field, parseFloat(e.target.value) || 0),
        className: inputClass,
        required: !!f.required,
        placeholder: f.help || '',
        pattern,
      })

    case 'date':
      return React.createElement('input', {
        type: 'date',
        value: strValue,
        onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(f.field, e.target.value),
        className: inputClass,
        required: !!f.required,
      })

    case 'boolean':
      return React.createElement('label', { className: 'flex items-center gap-2 cursor-pointer' },
        React.createElement('input', {
          type: 'checkbox',
          checked: !!value,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(f.field, e.target.checked),
          className: 'w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500',
        }),
        React.createElement('span', { className: 'text-sm text-gray-600' }, f.help || 'Sí/No'),
      )

    case 'select':
      return React.createElement('select', {
        value: strValue,
        onChange: (e: React.ChangeEvent<HTMLSelectElement>) => onChange(f.field, e.target.value),
        className: inputClass,
        required: !!f.required,
      },
        React.createElement('option', { value: '' }, 'Seleccionar...'),
        ...(f.options || []).map((opt) =>
          React.createElement('option', { key: opt, value: opt }, opt),
        ),
      )

    case 'textarea':
      return React.createElement('textarea', {
        value: strValue,
        onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => onChange(f.field, e.target.value),
        className: inputClass,
        rows: 3,
        required: !!f.required,
        placeholder: f.help || '',
      })

    case 'email':
      return React.createElement('input', {
        type: 'email',
        value: strValue,
        onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(f.field, e.target.value),
        className: inputClass,
        required: !!f.required,
        placeholder: f.help || '',
        pattern,
      })

    default: // text
      return React.createElement('input', {
        type: 'text',
        value: strValue,
        onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(f.field, e.target.value),
        className: inputClass,
        required: !!f.required,
        placeholder: f.help || '',
        pattern,
      })
  }
}
