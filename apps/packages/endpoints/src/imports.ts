const BASE = '/api/v1/tenant/imports'
const PUBLIC_BASE = '/api/v1/imports'
const PUBLIC_V2_BASE = '/api/v2/imports'

export const IMPORTS = {
  base: BASE,
  public: {
    base: PUBLIC_BASE,
    preview: `${PUBLIC_BASE}/preview`,
    uploadsAnalyze: `${PUBLIC_BASE}/uploads/analyze`,
    filesClassify: `${PUBLIC_BASE}/files/classify`,
    filesClassifyWithAI: `${PUBLIC_BASE}/files/classify-with-ai`,
    aiHealth: `${PUBLIC_BASE}/ai/health`,
    aiTelemetry: `${PUBLIC_BASE}/ai/telemetry`,
  },
  feedback: {
    base: `${PUBLIC_V2_BASE}/feedback`,
    stats: `${PUBLIC_V2_BASE}/feedback/stats`,
  },
  excel: {
    parse: `${BASE}/excel/parse`,
  },
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
    retry: (batchId: string) => `${BASE}/batches/${batchId}/retry`,
    reprocess: (batchId: string) => `${BASE}/batches/${batchId}/reprocess`,
    classifyAndPersist: (batchId: string) => `${BASE}/batches/${batchId}/classify-and-persist`,
    updateClassification: (batchId: string) => `${BASE}/batches/${batchId}/classification`,
    bulkPatchItems: (batchId: string) => `${BASE}/batches/${batchId}/items/bulk-patch`,
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
    promote: `${BASE}/items/promote`,
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
  processDocument: `${BASE}/process`,
  ocrJob: (jobId: string) => `${BASE}/jobs/${jobId}`,
}
