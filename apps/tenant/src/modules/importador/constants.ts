export const IMPORTADOR_IMPORT_SESSION_KEY = 'importador.import.session.v1'

export const IMPORTADOR_COPY = {
  reimportButton: 'Reprocesar',
  rerunButton: 'Reprocesar',
  rerunHelpText: 'Si el resultado no te sirve, reprocesa y vuelve a revisarlo.',
  importSingleEyebrow: 'Carga directa',
  importFolderEyebrow: 'Carga masiva',
  importSingleTitle: 'Arrastra tus archivos aqui',
  reimportTitle: 'Sube otra vez el archivo',
  importSingleSubtitle: 'o haz clic para elegirlos manualmente',
  reimportSubtitle: 'Haz clic para elegir el archivo original.',
  importFolderTitle: 'Sube una carpeta completa',
  importFolderSubtitle: 'Procesa de una vez todos los archivos compatibles dentro de una misma carpeta',
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
