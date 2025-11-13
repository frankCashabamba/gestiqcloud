import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

function pkgPath(p: string) {
  return path.resolve(__dirname, p)
}

const alias = {
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
}

export default defineConfig({
  plugins: [react()],
  resolve: { alias },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      exclude: [
        'node_modules/',
        'dist/',
        'src/__tests__/',
        '**/*.config.ts',
        '**/*.config.js',
        '**/types.ts',
        '**/manifest.ts',
      ]
    },
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', '.git'],
  }
})
