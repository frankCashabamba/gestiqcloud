import { registerSW } from 'virtual:pwa-register';
export function setupPWA(onEvent) {
    var updateSW = registerSW({
        immediate: true,
        onNeedRefresh: function () {
            window.dispatchEvent(new Event('pwa:need-refresh'));
            onEvent === null || onEvent === void 0 ? void 0 : onEvent('need-refresh');
        },
        onOfflineReady: function () {
            window.dispatchEvent(new Event('pwa:offline-ready'));
            onEvent === null || onEvent === void 0 ? void 0 : onEvent('offline-ready');
        }
    });
    window.__updateSW = updateSW;
    return updateSW;
}
