import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'node:fs'
import path from 'node:path'

const rawBase = process.env.VITE_BASE_PATH || '/admin/'
const basePath = rawBase.endsWith('/') ? rawBase : `${rawBase}/`

const buildId = process.env.VITE_BUILD_ID || new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)

function pkgPath(p: string) {
  return new URL(p, import.meta.url).pathname
}

function exists(p: string) {
  try { return fs.existsSync(p) } catch { return false }
}

// Construye alias apuntando a packages si existen; si no, siguen apuntando igual (los shims ya están creados)
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
  // Ensure deps required by shared packages resolve from this app
  'react-router-dom': pkgPath('./node_modules/react-router-dom'),
  'axios': pkgPath('./node_modules/axios'),
  'idb-keyval': pkgPath('./node_modules/idb-keyval'),
}

export default defineConfig({
  base: basePath,
  define: {
    __APP_BUILD_ID__: JSON.stringify(buildId),
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.0.0')
  },
  resolve: { alias },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      injectRegister: null,
      includeAssets: ['offline.html', 'index.html'],
      manifest: {
        name: 'GestiqCloud Admin',
        short_name: 'Admin',
        start_url: basePath,
        scope: basePath,
        display: 'standalone',
        theme_color: '#0f172a',
        background_color: '#ffffff',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      }
    })
  ],
  build: { outDir: 'dist' }
})
