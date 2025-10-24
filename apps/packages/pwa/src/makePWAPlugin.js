import { VitePWA } from 'vite-plugin-pwa';
export function makePWAPlugin(opts) {
    var _a;
    var scope = (_a = opts.scope) !== null && _a !== void 0 ? _a : '/';
    return VitePWA({
        registerType: 'autoUpdate',
        strategies: 'injectManifest',
        srcDir: 'src',
        filename: 'sw.js',
        injectRegister: null,
        includeAssets: ['offline.html', 'index.html'],
        manifest: {
            name: opts.appName,
            short_name: opts.appName,
            start_url: scope,
            scope: scope,
            display: 'standalone',
            theme_color: '#0f172a',
            background_color: '#ffffff',
            icons: [
                { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
                { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
                { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
            ]
        }
    });
}
