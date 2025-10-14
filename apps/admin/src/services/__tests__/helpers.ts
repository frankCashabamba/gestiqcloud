import { vi } from 'vitest'

export type ApiMockSpies = {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

export type ApiMockOptions = {
  getReturn?: unknown
  postReturn?: unknown
  putReturn?: unknown
  deleteReturn?: unknown
  getMock?: ReturnType<typeof vi.fn>
  postMock?: ReturnType<typeof vi.fn>
  putMock?: ReturnType<typeof vi.fn>
  deleteMock?: ReturnType<typeof vi.fn>
}

export async function loadServiceModule<T>(modulePath: string, options: ApiMockOptions = {}) {
  vi.resetModules()

  const get = options.getMock ?? vi.fn().mockResolvedValue({ data: options.getReturn })
  const post = options.postMock ?? vi.fn().mockResolvedValue({ data: options.postReturn })
  const put = options.putMock ?? vi.fn().mockResolvedValue({ data: options.putReturn })
  const del = options.deleteMock ?? vi.fn().mockResolvedValue({ data: options.deleteReturn })

  vi.doMock('../shared/api/client', () => ({
    default: {
      get,
      post,
      put,
      delete: del,
    },
  }))

  const module = (await import(modulePath)) as T

  return {
    module,
    api: { get, post, put, delete: del } satisfies ApiMockSpies,
  }
}

export function restoreModules() {
  vi.resetModules()
  vi.unmock('../shared/api/client')
  vi.clearAllMocks()
}
