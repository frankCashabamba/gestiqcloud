// apps/tenant/src/modules/inventario/manifest.ts
export const inventarioManifest = {
  id: 'inventory',
  name: 'Inventory',
  icon: '📦',
  path: '/inventory',
  enabled: true,
  requiredRole: 'operario',
  description: 'Stock control, movements and inventory valuation',
  features: [
    'Current stock view by warehouse',
    'Entry/exit movements',
    'Configurable low stock alerts',
    'Email/WhatsApp/Telegram notifications',
    'Inventory adjustments',
    'Batches and expiry dates',
    'CSV export',
  ],
}

// Alias para compatibilidad
export const manifest = inventarioManifest
