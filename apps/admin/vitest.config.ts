import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

function pkgPath(p: string) {
  return fileURLToPath(new URL(p, import.meta.url))
}

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/__tests__/**'],
    },
  },
  resolve: {
    alias: {
      '@ui': pkgPath('../packages/ui/src'),
      '@assets': pkgPath('../packages/assets'),
      '@pwa': pkgPath('../packages/pwa/src'),
      '@shared/http': pkgPath('../packages/http-core/src'),
      '@shared/endpoints': pkgPath('../packages/endpoints/src'),
      '@shared/auth-core': pkgPath('../packages/auth-core/src'),
      '@shared/ui': pkgPath('../packages/ui/src'),
      '@shared/domain': pkgPath('../packages/domain/src'),
      '@shared/utils': pkgPath('../packages/utils/src'),
      '@shared/telemetry': pkgPath('../packages/telemetry/src'),
      '@shared': pkgPath('../packages/shared/src'),
      zod: pkgPath('../packages/zod/index.ts'),
      'react-router-dom': pkgPath('./node_modules/react-router-dom'),
      'axios': pkgPath('./node_modules/axios'),
      'idb-keyval': pkgPath('./node_modules/idb-keyval'),
    },
  },
})
