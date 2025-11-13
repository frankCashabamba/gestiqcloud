/**
 * useSectorValidation
 * 
 * Hook para validaciones específicas del sector activo
 * Retorna función de validación que aplica reglas según plantilla
 */
import { useTenantFeatures, useTenantSector } from '../contexts/TenantConfigContext'

export interface ValidationError {
  field: string
  message: string
  level: 'error' | 'warning'
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
  warnings: ValidationError[]
}

/**
 * Hook que retorna función de validación personalizada por sector
 * 
 * @example
 * ```tsx
 * const { validate } = useSectorValidation()
 * 
 * const result = validate(formData, 'product')
 * if (!result.valid) {
 *   console.error('Errores:', result.errors)
 * }
 * ```
 */
export function useSectorValidation() {
  const features = useTenantFeatures()
  const sector = useTenantSector()

  /**
   * Valida un formulario según las reglas del sector
   * 
   * @param formData - Datos del formulario a validar
   * @param context - Contexto de validación ('product', 'inventory', 'sale')
   * @returns Resultado de validación con errores y warnings
   */
  const validate = (
    formData: any, 
    context: 'product' | 'inventory' | 'sale' | 'customer'
  ): ValidationResult => {
    const errors: ValidationError[] = []
    const warnings: ValidationError[] = []

    // ============================================
    // VALIDACIONES DE PRODUCTO
    // ============================================
    if (context === 'product') {
      // Panadería: Fecha de caducidad obligatoria
      if (sector.is_panaderia && features.inventory_expiry_tracking) {
        if (!formData.expires_at) {
          errors.push({
            field: 'expires_at',
            message: 'Productos de panadería requieren fecha de caducidad',
            level: 'error'
          })
        } else {
          const expiryDate = new Date(formData.expires_at)
          const today = new Date()
          const daysUntilExpiry = Math.ceil((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

          if (daysUntilExpiry < 0) {
            errors.push({
              field: 'expires_at',
              message: 'La fecha de caducidad no puede ser anterior a hoy',
              level: 'error'
            })
          }

          if (daysUntilExpiry > 30) {
            warnings.push({
              field: 'expires_at',
              message: 'Fecha de caducidad inusualmente lejana para productos de panadería',
              level: 'warning'
            })
          }
        }
      }

      // Taller: Código OEM recomendado
      if (sector.is_taller) {
        if (!formData.codigo_oem) {
          warnings.push({
            field: 'codigo_oem',
            message: 'Se recomienda añadir código OEM para repuestos',
            level: 'warning'
          })
        }

        if (!formData.marca_vehiculo || !formData.modelo_compatible) {
          warnings.push({
            field: 'marca_vehiculo',
            message: 'Especificar compatibilidad facilita la búsqueda de repuestos',
            level: 'warning'
          })
        }
      }

      // Retail: SKU único obligatorio
      if (sector.is_retail) {
        if (!formData.sku || formData.sku.trim() === '') {
          errors.push({
            field: 'sku',
            message: 'El código SKU es obligatorio para productos de retail',
            level: 'error'
          })
        }
      }

      // Venta por peso: validar unidad
      if (features.pos_enable_weights && formData.sold_by_weight) {
        if (!formData.weight_unit) {
          errors.push({
            field: 'weight_unit',
            message: 'Debe especificar la unidad de peso',
            level: 'error'
          })
        }
      }

      // price: validación general
      if (!formData.precio_venta || parseFloat(formData.precio_venta) <= 0) {
        errors.push({
          field: 'precio_venta',
          message: 'El precio de venta debe ser mayor a 0',
          level: 'error'
        })
      }

      if (formData.precio_compra && formData.precio_venta) {
        const compra = parseFloat(formData.precio_compra)
        const venta = parseFloat(formData.precio_venta)
        
        if (venta < compra) {
          warnings.push({
            field: 'precio_venta',
            message: 'El precio de venta es menor al precio de compra (margen negativo)',
            level: 'warning'
          })
        }
      }
    }

    // ============================================
    // VALIDACIONES DE INVENTARIO
    // ============================================
    if (context === 'inventory') {
      // Fecha de caducidad en movimientos de entrada
      if (features.inventory_expiry_tracking && sector.is_panaderia) {
        if (!formData.expires_at) {
          errors.push({
            field: 'expires_at',
            message: 'Fecha de caducidad obligatoria para productos de panadería',
            level: 'error'
          })
        }
      }

      // Lote en movimientos de entrada (taller)
      if (features.inventory_lot_tracking && sector.is_taller) {
        if (!formData.lot) {
          warnings.push({
            field: 'lot',
            message: 'Se recomienda registrar el lote de fabricación',
            level: 'warning'
          })
        }
      }

      // Cantidad debe ser > 0
      if (!formData.quantity || parseFloat(formData.quantity) <= 0) {
        errors.push({
          field: 'quantity',
          message: 'La cantidad debe ser mayor a 0',
          level: 'error'
        })
      }

      // Ajustes requieren justificación
      if (formData.move_type === 'adjustment' && !formData.notes) {
        errors.push({
          field: 'notes',
          message: 'Los ajustes de inventario requieren justificación',
          level: 'error'
        })
      }

      // Transferencias requieren destino
      if (formData.move_type === 'transfer' && !formData.destination_warehouse) {
        errors.push({
          field: 'destination_warehouse',
          message: 'Debe especificar el almacén de destino',
          level: 'error'
        })
      }
    }

    // ============================================
    // VALIDACIONES DE VENTA
    // ============================================
    if (context === 'sale') {
      // Validar que haya líneas
      if (!formData.lines || formData.lines.length === 0) {
        errors.push({
          field: 'lines',
          message: 'La venta debe tener al menos un producto',
          level: 'error'
        })
      }

      // Validar cada línea
      formData.lines?.forEach((line: any, index: number) => {
        if (!line.quantity || parseFloat(line.quantity) <= 0) {
          errors.push({
            field: `lines[${index}].quantity`,
            message: `Línea ${index + 1}: La cantidad debe ser mayor a 0`,
            level: 'error'
          })
        }

        if (!line.unit_price || parseFloat(line.unit_price) <= 0) {
          errors.push({
            field: `lines[${index}].unit_price`,
            message: `Línea ${index + 1}: El precio debe ser mayor a 0`,
            level: 'error'
          })
        }
      })

      // Cliente requerido para facturas (España)
      if (formData.doc_type === 'invoice' && formData.country === 'ES') {
        if (!formData.customer_tax_id) {
          errors.push({
            field: 'customer_tax_id',
            message: 'Las facturas requieren NIF/CIF del cliente',
            level: 'error'
          })
        }
      }
    }

    // ============================================
    // VALIDACIONES DE CLIENTE
    // ============================================
    if (context === 'customer') {
      // Nombre obligatorio
      if (!formData.name || formData.name.trim() === '') {
        errors.push({
          field: 'name',
          message: 'El nombre del cliente es obligatorio',
          level: 'error'
        })
      }

      // Validar NIF/CIF España
      if (formData.country === 'ES' && formData.tax_id) {
        if (!validateNIF(formData.tax_id)) {
          warnings.push({
            field: 'tax_id',
            message: 'El formato del NIF/CIF no parece válido',
            level: 'warning'
          })
        }
      }

      // Validar RUC/Cédula Ecuador
      if (formData.country === 'EC' && formData.tax_id) {
        if (!validateRUC(formData.tax_id)) {
          warnings.push({
            field: 'tax_id',
            message: 'El formato del RUC/Cédula no parece válido',
            level: 'warning'
          })
        }
      }

      // Email formato
      if (formData.email && !validateEmail(formData.email)) {
        errors.push({
          field: 'email',
          message: 'El formato del email no es válido',
          level: 'error'
        })
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings
    }
  }

  return {
    validate,
    features,
    sector
  }
}

// ============================================
// HELPERS DE VALIDACIÓN
// ============================================

/**
 * Valida formato básico de NIF/CIF español
 */
function validateNIF(nif: string): boolean {
  const nifRegex = /^[0-9XYZ][0-9]{7}[A-Z]$/i
  return nifRegex.test(nif.replace(/[\s-]/g, ''))
}

/**
 * Valida formato básico de RUC/Cédula ecuatoriano
 */
function validateRUC(tax_id: string): boolean {
  const rucRegex = /^[0-9]{10,13}$/
  return rucRegex.test(tax_id.replace(/[\s-]/g, ''))
}

/**
 * Valida formato de email
 */
function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export default useSectorValidation
