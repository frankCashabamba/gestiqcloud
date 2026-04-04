export const IMPORTADOR_UPLOADER_SESSION_KEY = 'importador.uploader.session.v1'

export const IMPORTADOR_COPY = {
  reimportButton: 'Reprocesar',
  rerunButton: 'Reprocesar',
  rerunHelpText: 'Si el resultado no te sirve, reprocesa y vuelve a revisarlo.',
  uploadSingleEyebrow: 'Carga directa',
  uploadFolderEyebrow: 'Carga masiva',
  uploadSingleTitle: 'Arrastra tus archivos aqui',
  uploadReimportTitle: 'Sube otra vez el archivo',
  uploadSingleSubtitle: 'o haz clic para elegirlos manualmente',
  uploadReimportSubtitle: 'Haz clic para elegir el archivo original.',
  uploadFolderTitle: 'Sube una carpeta completa',
  uploadFolderSubtitle: 'Procesa de una vez todos los archivos compatibles dentro de una misma carpeta',
  reimportCheckboxLabel: 'Reprocesar este archivo',
  reimportCheckboxHint: '(solo si quieres rehacer el analisis del mismo archivo)',
} as const

export const IMPORTADOR_FLOW_STEPS = [
  { step: 1, label: 'Carga' },
  { step: 2, label: 'Espera' },
  { step: 3, label: 'Revisa' },
  { step: 4, label: 'Guarda' },
] as const

export const IMPORTADOR_DESTINATION_LABELS = {
  recipe: 'Receta',
  expense: 'Gasto',
  supplier_invoice: 'Factura proveedor',
} as const

export function getImportadorSaveActionLabel(destination: 'recipe' | 'expense' | 'supplier_invoice'): string {
  switch (destination) {
    case 'recipe':
      return 'Guardar receta'
    case 'supplier_invoice':
      return 'Guardar factura'
    default:
      return 'Guardar gasto'
  }
}

export function getImportadorSavedAsLabel(savedAs?: 'expense' | 'supplier_invoice' | 'products' | string | null): string {
  switch (savedAs) {
    case 'products':
      return 'Productos guardados'
    case 'supplier_invoice':
      return 'Guardado como factura de compra'
    case 'expense':
      return 'Guardado como gasto'
    default:
      return 'Documento guardado'
  }
}

export const FIELD_LABELS: Record<string, string> = {
  vendor: 'Proveedor',
  vendor_tax_id: 'RUC proveedor',
  customer: 'Cliente',
  customer_tax_id: 'Documento cliente',
  category: 'Categoria',
  concept: 'Concepto',
  currency: 'Moneda',
  subtotal: 'Subtotal',
  tax_amount: 'Impuesto',
  total_amount: 'Total',
  payment_terms: 'Importe reportado',
  payment_method: 'Forma de pago',
  issue_date: 'Fecha de emision',
  due_date: 'Fecha de vencimiento',
  doc_number: 'Numero de documento',
  invoice_number: 'Numero de factura',
  reference: 'Referencia',
  description: 'Descripcion',
  product: 'Producto',
  quantity: 'Cantidad',
  qty: 'Cantidad',
  unit_price: 'Precio unitario',
  line_total: 'Total de linea',
}

export const STATUS_LABELS: Record<string, string> = {
  REVIEW: 'Por revisar',
  CONFIRMED: 'Confirmado',
  FAILED: 'Con error',
  PROCESSING: 'Procesando',
  PENDING: 'En cola',
  INVALID: 'Con error',
  REPROCESS: 'Pendiente de nueva revision',
  VALID: 'Valido',
  IMPORTED: 'Guardado',
}

export function formatFieldLabel(key: string): string {
  if (!key) return ''
  if (FIELD_LABELS[key]) return FIELD_LABELS[key]
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
