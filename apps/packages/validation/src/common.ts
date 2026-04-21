/**
 * Validaciones comunes reutilizables
 */

export const commonValidations = {
  // Validaciones de texto
  required: (value: string) => {
    if (!value || value.trim() === '') {
      return 'Este campo es requerido'
    }
    return null
  },

  minLength: (min: number) => (value: string) => {
    if (!value || value.length < min) {
      return `Debe tener al menos ${min} caracteres`
    }
    return null
  },

  maxLength: (max: number) => (value: string) => {
    if (value && value.length > max) {
      return `No puede tener más de ${max} caracteres`
    }
    return null
  },

  email: (value: string) => {
    if (!value) return null
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(value)) {
      return 'Ingrese un email válido'
    }
    return null
  },

  phone: (value: string) => {
    if (!value) return null
    const phoneRegex = /^\+?[\d\s\-()]+$/
    if (!phoneRegex.test(value)) {
      return 'Ingrese un teléfono válido'
    }
    return null
  },

  // Validaciones numéricas
  number: (value: string) => {
    if (!value) return null
    if (isNaN(Number(value))) {
      return 'Debe ser un número válido'
    }
    return null
  },

  positive: (value: number) => {
    if (value <= 0) {
      return 'Debe ser un número positivo'
    }
    return null
  },

  min: (min: number) => (value: number) => {
    if (value < min) {
      return `Debe ser mayor o igual a ${min}`
    }
    return null
  },

  max: (max: number) => (value: number) => {
    if (value > max) {
      return `Debe ser menor o igual a ${max}`
    }
    return null
  },

  // Validaciones de selección
  requiredSelect: (value: any) => {
    if (value === undefined || value === null || value === '') {
      return 'Debe seleccionar una opción'
    }
    return null
  },

  // Validaciones de fechas
  date: (value: string) => {
    if (!value) return null
    const date = new Date(value)
    if (isNaN(date.getTime())) {
      return 'Ingrese una fecha válida'
    }
    return null
  },

  minDate: (minDate: Date) => (value: string) => {
    if (!value) return null
    const date = new Date(value)
    if (date < minDate) {
      return `La fecha debe ser posterior a ${minDate.toLocaleDateString()}`
    }
    return null
  },

  maxDate: (maxDate: Date) => (value: string) => {
    if (!value) return null
    const date = new Date(value)
    if (date > maxDate) {
      return `La fecha debe ser anterior a ${maxDate.toLocaleDateString()}`
    }
    return null
  },

  // Validaciones de archivos
  fileSize: (maxSizeMB: number) => (file: File) => {
    if (!file) return null
    const maxSizeBytes = maxSizeMB * 1024 * 1024
    if (file.size > maxSizeBytes) {
      return `El archivo no puede superar ${maxSizeMB}MB`
    }
    return null
  },

  fileType: (allowedTypes: string[]) => (file: File) => {
    if (!file) return null
    if (!allowedTypes.includes(file.type)) {
      return `Tipo de archivo no permitido. Tipos válidos: ${allowedTypes.join(', ')}`
    }
    return null
  }
}
