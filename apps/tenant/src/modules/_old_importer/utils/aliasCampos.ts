import type { EntityTypeConfig } from '../config/entityTypes'

export function getAliasSugeridos(config?: EntityTypeConfig) {
  if (config) {
    return config.fields.reduce<Record<string, string[]>>((acc, field) => {
      acc[field.field] = field.aliases || []
      return acc
    }, {})
  }

  return {
    fecha: ['fecha', 'date', 'fecha_emision', 'fch'],
    concepto: ['concepto', 'descripcion', 'detalle', 'desc'],
    monto: ['monto', 'importe', 'total', 'valor'],
  } as Record<string, string[]>
}
