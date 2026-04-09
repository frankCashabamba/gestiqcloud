export const IMPORTADOR_IMPORT_SESSION_KEY = 'importador.import.session.v1'

export const IMPORTADOR_COPY = {
  reprocessFastButton: 'Fast reprocess',
  reprocessDeepButton: 'Deep review',
  reprocessFastHelpText: 'Reuses cache and the fast routes. It does not promise a better result.',
  reprocessDeepHelpText: 'Ignores caches and retries with more extraction depth. Takes longer.',
  importSingleEyebrow: 'Direct upload',
  importFolderEyebrow: 'Bulk upload',
  importSingleTitle: 'Drop your files here',
  reimportTitle: 'Reprocess this document',
  importSingleSubtitle: 'or click to select them manually',
  reimportSubtitle: 'Choose the reprocess mode before uploading the original file again.',
  reimportFastSubtitle: 'Fast mode: keeps the current behavior and may reuse cache.',
  reimportDeepSubtitle: 'Deep mode: starts over to improve extraction.',
  importFolderTitle: 'Upload a full folder',
  importFolderSubtitle: 'Process all compatible files inside a single folder at once',
  reimportModeLabel: 'Reprocess mode',
  reimportModeFastLabel: 'Fast',
  reimportModeDeepLabel: 'Deep',
  reimportModeFastHint: 'Same path as today: cache, rules, and fast routes.',
  reimportModeDeepHint: 'Clears OCR/AI cache and retries missing fields.',
  reimportModeDeepFootnote: 'This is the only mode prepared to use a premium provider in the future.',
} as const

export const IMPORTADOR_FLOW_STEPS = [
  { step: 1, label: 'Upload' },
  { step: 2, label: 'Wait' },
  { step: 3, label: 'Review' },
  { step: 4, label: 'Save' },
] as const

export const IMPORTADOR_DESTINATION_LABELS = {
  recipe: 'Recipe',
  expense: 'Expense',
  supplier_invoice: 'Supplier invoice',
} as const

export function getImportadorSaveActionLabel(destination: 'recipe' | 'expense' | 'supplier_invoice'): string {
  switch (destination) {
    case 'recipe':
      return 'Save recipe'
    case 'supplier_invoice':
      return 'Save invoice'
    default:
      return 'Save expense'
  }
}

export function getImportadorSavedAsLabel(savedAs?: 'expense' | 'supplier_invoice' | 'products' | string | null): string {
  switch (savedAs) {
    case 'products':
      return 'Saved products'
    case 'supplier_invoice':
      return 'Saved as supplier invoice'
    case 'expense':
      return 'Saved as expense'
    default:
      return 'Document saved'
  }
}

export const STATUS_LABELS: Record<string, string> = {
  REVIEW: 'Needs review',
  CONFIRMED: 'Confirmed',
  FAILED: 'Failed',
  PROCESSING: 'Processing',
  PENDING: 'Queued',
  INVALID: 'Failed',
  REPROCESS: 'Needs another review',
  VALID: 'Valid',
  IMPORTED: 'Saved',
}
