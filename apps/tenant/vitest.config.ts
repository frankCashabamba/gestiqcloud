import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const dirname = path.dirname(fileURLToPath(import.meta.url))
const resolveFromApp = (relative: string) => path.resolve(dirname, relative)

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@shared/http': resolveFromApp('../packages/http-core/src'),
      '@shared/endpoints': resolveFromApp('../packages/endpoints/src'),
      '@shared': resolveFromApp('../packages/shared/src'),
      '@shared/utils': resolveFromApp('../packages/utils/src'),
      '@shared/ui': resolveFromApp('../packages/ui/src'),
      '@shared/domain': resolveFromApp('../packages/domain/src'),
      '@shared/telemetry': resolveFromApp('../packages/telemetry/src'),
      '@ui': resolveFromApp('../packages/ui/src'),
      '@assets': resolveFromApp('../packages/assets'),
      '@pwa': resolveFromApp('../packages/pwa/src'),
      zod: resolveFromApp('../packages/zod/index.ts'),
    },
  },
})
