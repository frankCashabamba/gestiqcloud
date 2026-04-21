/**
 * Reglas de negocio específicas del dominio
 */

export const businessRules = {
  // Reglas de negocio para categorías
  categoriaGasto: {
    codigoUnico: async (codigo: string, excludeId?: number) => {
      // Lógica para verificar si el código ya existe
      // Esto se implementaría con una llamada a la API
      return null // null si es válido, string con error si no
    },

    nombreRequerido: (nombre: string) => {
      if (!nombre || nombre.trim() === '') {
        return 'El nombre de la categoría es requerido'
      }
      return null
    },

    codigoFormato: (codigo: string) => {
      if (!codigo || codigo.trim() === '') {
        return 'El código es requerido'
      }
      if (!/^[A-Z0-9_]+$/.test(codigo)) {
        return 'El código solo puede contener mayúsculas, números y guiones bajos'
      }
      return null
    }
  },

  // Reglas de negocio para productos
  producto: {
    skuUnico: async (sku: string, excludeId?: number) => {
      return null
    },

    precioPositivo: (precio: number) => {
      if (precio <= 0) {
        return 'El precio debe ser mayor a 0'
      }
      return null
    },

    stockMinimo: (stock: number) => {
      if (stock < 0) {
        return 'El stock no puede ser negativo'
      }
      return null
    }
  },

  // Reglas de negocio para usuarios
  usuario: {
    emailUnico: async (email: string, excludeId?: number) => {
      return null
    },

    passwordSeguro: (password: string) => {
      if (!password || password.length < 8) {
        return 'La contraseña debe tener al menos 8 caracteres'
      }
      if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
        return 'La contraseña debe contener mayúsculas, minúsculas y números'
      }
      return null
    },

    rolRequerido: (rolId: number) => {
      if (!rolId || rolId <= 0) {
        return 'Debe seleccionar un rol válido'
      }
      return null
    }
  },

  // Reglas de negocio para empresas
  empresa: {
    rucValido: (ruc: string) => {
      if (!ruc || ruc.trim() === '') {
        return 'El RUC es requerido'
      }
      // Validación específica para Ecuador (13 dígitos)
      if (!/^\d{13}$/.test(ruc)) {
        return 'El RUC debe tener 13 dígitos'
      }
      return null
    },

    nombreComercialRequerido: (nombre: string) => {
      if (!nombre || nombre.trim() === '') {
        return 'El nombre comercial es requerido'
      }
      return null
    }
  }
}
