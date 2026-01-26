import React from 'react'
import { render, waitFor, act } from '@testing-library/react'

// Mock env before importing the module
const originalEnv = (globalThis as any).__IMPORTS_ENV__

jest.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'token-123' }),
}))

jest.mock('../services/parseExcelFile', () => ({
  parseExcelFile: jest.fn().mockResolvedValue({ headers: [], rows: [] }),
}))

const uploadExcelViaChunks = jest.fn()
const createBatch = jest.fn().mockResolvedValue({ id: 'batch-1' })
const ingestBatch = jest.fn().mockResolvedValue({ accepted: 1, rejected: 0 })
const processDocument = jest.fn()
const pollOcrJob = jest.fn()

jest.mock('../services/importsApi', () => ({
  uploadExcelViaChunks: (...args: any[]) => uploadExcelViaChunks(...args),
  createBatch: (...args: any[]) => createBatch(...args),
  ingestBatch: (...args: any[]) => ingestBatch(...args),
  processDocument: (...args: any[]) => processDocument(...args),
  pollOcrJob: (...args: any[]) => pollOcrJob(...args),
  listMappings: jest.fn().mockResolvedValue([]),
}))

describe('ImportQueueContext', () => {
  let ImportQueueProvider: any
  let useImportQueue: any

  beforeEach(async () => {
    jest.resetModules()
    ;(globalThis as any).__IMPORTS_ENV__ = {
      VITE_IMPORTS_CHUNK_THRESHOLD_MB: '0.0001',
      VITE_IMPORTS_JOB_RECHECK_INTERVAL: '5',
    }
    const mod = await import('../context/ImportQueueContext')
    ImportQueueProvider = mod.ImportQueueProvider
    useImportQueue = mod.useImportQueue
    uploadExcelViaChunks.mockReset()
    createBatch.mockClear()
    ingestBatch.mockClear()
    processDocument.mockReset()
    pollOcrJob.mockReset()
  })

  afterAll(() => {
    jest.useRealTimers()
    ;(globalThis as any).__IMPORTS_ENV__ = originalEnv
  })

  it('usa chunked upload cuando el archivo supera el umbral', async () => {
    jest.useFakeTimers()
    uploadExcelViaChunks.mockResolvedValue({ batchId: 'batch-xyz', fileKey: 'fk', taskId: 't' })

    const state: any = {}
    const Consumer = () => {
      const ctx = useImportQueue()
      state.ctx = ctx
      return null
    }

    render(
      <ImportQueueProvider>
        <Consumer />
      </ImportQueueProvider>
    )

    const bigFile = new File([new Uint8Array(2 * 1024 * 1024)], 'big.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    act(() => {
      state.ctx.addToQueue([bigFile])
      jest.runAllTimers()
    })

    await waitFor(() => expect(uploadExcelViaChunks).toHaveBeenCalled())
    await waitFor(() => expect(state.ctx.queue[0].status).toBe('saved'))
  })

  it('reintenta OCR con poll cuando el job sigue pendiente', async () => {
    jest.useFakeTimers()
    processDocument.mockResolvedValueOnce({ status: 'pending', jobId: 'job-1' })
    pollOcrJob.mockResolvedValueOnce({
      status: 'done',
      jobId: 'job-1',
      payload: { documentos: [{ documentoTipo: 'factura', campo: 'a' }] },
    })

    const state: any = {}
    const Consumer = () => {
      const ctx = useImportQueue()
      state.ctx = ctx
      return null
    }

    render(
      <ImportQueueProvider>
        <Consumer />
      </ImportQueueProvider>
    )

    const pdfFile = new File([new Uint8Array([1, 2, 3])], 'doc.pdf', { type: 'application/pdf' })

    act(() => {
      state.ctx.addToQueue([pdfFile])
      jest.runAllTimers()
    })

    // Primera vuelta: enqueue OCR job
    await waitFor(() => expect(processDocument).toHaveBeenCalled())

    // Avanzar al reintento
    act(() => {
      jest.runOnlyPendingTimers()
    })

    await waitFor(() => expect(pollOcrJob).toHaveBeenCalledWith('job-1', 'token-123'))
    await waitFor(() => expect(state.ctx.queue[0].status).toBe('ready'))
    expect(state.ctx.queue[0].docType).toBe('invoices')
  })
})
