/**
 * Tipos para validaciones
 */

export interface ValidationRule {
  required?: boolean
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  min?: number
  max?: number
  email?: boolean
  url?: boolean
}

export interface ValidationResult {
  isValid: boolean
  error?: string
}

export interface FormFieldConfig {
  name: string
  label: string
  type: 'text' | 'email' | 'number' | 'select' | 'textarea' | 'checkbox' | 'date'
  required?: boolean
  placeholder?: string
  options?: Array<{ value: string; label: string }>
  validation?: ValidationRule
  disabled?: boolean
  defaultValue?: any
}
