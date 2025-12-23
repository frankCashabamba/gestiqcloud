const BASE = '/api/v1/tenant/imports'

export const IMPORTS = {
  base: BASE,
  batches: {
    base: `${BASE}/batches`,
    byId: (id: string) => `${BASE}/batches/${id}`,
    ingest: (id: string, columnMappingId?: string | null) =>
      columnMappingId
        ? `${BASE}/batches/${id}/ingest?column_mapping_id=${columnMappingId}`
        : `${BASE}/batches/${id}/ingest`,
    items: (batchId: string, qs = '') => `${BASE}/batches/${batchId}/items${qs}`,
    itemsProducts: (batchId: string, qs = '') => `${BASE}/batches/${batchId}/items/products${qs}`,
    itemsValidate: (batchId: string) => `${BASE}/batches/${batchId}/validate`,
    promote: (batchId: string) => `${BASE}/batches/${batchId}/promote`,
    setMapping: (batchId: string) => `${BASE}/batches/${batchId}/set-mapping`,
    reset: (batchId: string) => `${BASE}/batches/${batchId}/reset`,
    delete: (batchId: string) => `${BASE}/batches/${batchId}`,
    cancel: (batchId: string) => `${BASE}/batches/${batchId}/cancel`,
    fromUpload: `${BASE}/batches/from-upload`,
    startExcel: (batchId: string) => `${BASE}/batches/${batchId}/start-excel-import`,
    status: (batchId: string) => `${BASE}/batches/${batchId}/status`,
    confirm: (batchId: string) => `${BASE}/batches/${batchId}/confirm`,
    confirmationStatus: (batchId: string) => `${BASE}/batches/${batchId}/confirmation-status`,
  },
  reports: {
    errorsCsv: (batchId: string) => `${BASE}/batches/${batchId}/errors.csv`,
    batchPhotos: (batchId: string) => `${BASE}/batches/${batchId}/photos`,
    itemPhotos: (batchId: string, itemId: string) =>
      `${BASE}/batches/${batchId}/items/${itemId}/photos`,
  },
  items: {
    products: (qs = '') => `${BASE}/items/products${qs || ''}`,
    byId: (batchId: string, itemId: string) => `${BASE}/batches/${batchId}/items/${itemId}`,
    validateSingle: (batchId: string, itemId: string) =>
      `${BASE}/batches/${batchId}/items/${itemId}/validate`,
    deleteMultiple: `${BASE}/items/delete-multiple`,
  },
  uploads: {
    chunkInit: `${BASE}/uploads/chunk/init`,
    chunkPart: (uploadId: string, part: number | string) =>
      `${BASE}/uploads/chunk/${uploadId}/${part}`,
    chunkComplete: (uploadId: string) => `${BASE}/uploads/chunk/${uploadId}/complete`,
  },
  mappings: {
    list: `${BASE}/column-mappings`,
    legacyList: `${BASE}/mappings`,
    create: `${BASE}/column-mappings`,
    suggest: `${BASE}/mappings/suggest`,
  },
  parsersRegistry: `${BASE}/parsers/registry`,
  analyzeFile: `${BASE}/analyze-file`,
  processDocument: `${BASE}/procesar`,
  ocrJob: (jobId: string) => `${BASE}/jobs/${jobId}`,
}
