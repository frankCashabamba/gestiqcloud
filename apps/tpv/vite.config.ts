import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'icons/*.png'],
      manifest: {
        name: 'GestiQCloud TPV',
        short_name: 'TPV',
        description: 'Punto de Venta Universal - Offline First',
        theme_color: '#3b82f6',
        background_color: '#ffffff',
        display: 'fullscreen',
        orientation: 'landscape',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\/api\/v1\/products/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'products-cache',
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 60 * 60 * 24 // 24 horas
              }
            }
          },
          {
            urlPattern: /^https:\/\/.*\/api\/v1\/pos/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'pos-cache',
              networkTimeoutSeconds: 3
            }
          }
        ]
      }
    })
  ],
  server: {
    port: 8083,
    host: '0.0.0.0'
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
