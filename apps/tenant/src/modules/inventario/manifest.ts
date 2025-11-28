// apps/tenant/src/modules/inventario/manifest.ts
export const inventarioManifest = {
  id: 'inventario',
  name: 'Inventory',
  icon: '📦',
  path: '/inventario',
  enabled: true,
  requiredRole: 'operario',
  description: 'Control de stock, movimientos y valoración de inventario',
  features: [
    'Vista de stock actual por almacén',
    'Movimientos de entrada/salida',
    'Alertas configurables de stock bajo',
    'Notificaciones por email/WhatsApp/Telegram',
    'Ajustes de inventario',
    'Lotes y caducidades',
    'Exportación a CSV',
  ],
}

// Alias para compatibilidad
export const manifest = inventarioManifest
