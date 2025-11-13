import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath } from 'node:url';
var rawBase = process.env.VITE_BASE_PATH || '/';
var basePath = rawBase.endsWith('/') ? rawBase : "".concat(rawBase, "/");
var buildId = process.env.VITE_BUILD_ID || new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
function pkgPath(p) {
    return fileURLToPath(new URL(p, import.meta.url));
}
var alias = {
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
    // This one lives in the root-level packages dir, not apps/packages
    '@shared-lib': pkgPath('../../packages/shared/lib'),
    zod: pkgPath('../packages/zod/index.ts'),
    // Ensure deps required by shared packages resolve from this app
    'react-router-dom': pkgPath('./node_modules/react-router-dom'),
    'axios': pkgPath('./node_modules/axios'),
    'idb-keyval': pkgPath('./node_modules/idb-keyval'),
};
export default defineConfig({
    base: basePath,
    define: {
        __APP_BUILD_ID__: JSON.stringify(buildId),
        __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.0.0')
    },
    server: {
        host: process.env.HOST || '0.0.0.0',
        port: Number(process.env.PORT || 8082),
        strictPort: false,
        proxy: {
            '/api': {
                target: process.env.VITE_API_URL || 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
                // Preserve path as-is so /api/v1/* maps directly
                rewrite: function (path) { return path; },
            },
        },
    },
    resolve: { alias: alias, dedupe: ['react', 'react-dom'] },
    plugins: [
        react(),
        VitePWA({
            registerType: 'autoUpdate',
            strategies: 'injectManifest',
            srcDir: 'src',
            filename: 'sw.js',
            injectRegister: null,
            includeAssets: ['offline.html', 'index.html', 'icon.svg'],
            manifest: {
                name: 'GestiqCloud Tenant',
                short_name: 'Tenant',
                start_url: basePath,
                scope: basePath,
                display: 'standalone',
                theme_color: '#0f172a',
                background_color: '#ffffff',
                icons: [
                    { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }
                ]
            }
        })
    ],
    build: { outDir: 'dist' }
});
