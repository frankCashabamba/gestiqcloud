import { describe, expect, it } from 'vitest'

import { resolveRuntimeApiBase, resolveRuntimeAssetRoot } from './runtimeApi'

describe('runtimeApi', () => {
  it('uses same-origin api proxy for localhost dev/offline scenarios', () => {
    expect(resolveRuntimeApiBase('http://localhost:8000')).toBe('/api')
    expect(resolveRuntimeAssetRoot('http://localhost:8000')).toBe('')
  })

  it('keeps absolute remote api urls when frontend and api are on different hosts', () => {
    expect(resolveRuntimeApiBase('https://api.example.com')).toBe('https://api.example.com')
    expect(resolveRuntimeAssetRoot('https://api.example.com/api')).toBe('https://api.example.com')
  })
})
