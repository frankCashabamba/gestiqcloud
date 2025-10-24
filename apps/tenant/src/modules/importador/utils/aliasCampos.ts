export function getAliasSugeridos() {
  return {
    fecha: ['fecha', 'date', 'fecha_emision', 'fch'],
    concepto: ['concepto', 'descripcion', 'detalle', 'desc'],
    monto: ['monto', 'importe', 'total', 'valor'],
  } as Record<string, string[]>
}

