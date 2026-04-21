/**
 * Validaciones para formularios reutilizables
 */

export const formValidations = {
  // Validador completo para formularios
  validateField: (value: any, rules: any[]) => {
    for (const rule of rules) {
      if (typeof rule === 'function') {
        const error = rule(value)
        if (error) return error
      }
    }
    return null
  },

  // Validador de formulario completo
  validateForm: (data: Record<string, any>, schema: Record<string, any[]>) => {
    const errors: Record<string, string> = {}

    for (const [field, rules] of Object.entries(schema)) {
      const error = formValidations.validateField(data[field], rules)
      if (error) {
        errors[field] = error
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    }
  },

  // Transformaciones de datos
  transformations: {
    trim: (value: string) => value?.trim() || '',
    uppercase: (value: string) => value?.toUpperCase() || '',
    lowercase: (value: string) => value?.toLowerCase() || '',
    number: (value: string) => {
      const num = parseFloat(value)
      return isNaN(num) ? 0 : num
    },
    integer: (value: string) => {
      const num = parseInt(value)
      return isNaN(num) ? 0 : num
    }
  },

  // Máscaras y formateo
  masks: {
    ruc: (value: string) => {
      const digits = value.replace(/\D/g, '')
      return digits.slice(0, 13)
    },

    phone: (value: string) => {
      const digits = value.replace(/\D/g, '')
      if (digits.length <= 10) {
        return digits.replace(/(\d{4})(\d{3})(\d{3})/, '$1-$2-$3')
      }
      return digits
    },

    currency: (value: number) => {
      return new Intl.NumberFormat('es-EC', {
        style: 'currency',
        currency: 'USD'
      }).format(value)
    },

    percentage: (value: number) => {
      return `${(value * 100).toFixed(2)}%`
    }
  }
}
