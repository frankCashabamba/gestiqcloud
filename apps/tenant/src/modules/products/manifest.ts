// apps/tenant/src/modules/products/manifest.ts
export const productosManifest = {
  id: 'products',
  name: 'Productos',
  icon: '📦',
  path: '/products',
  enabled: true,
  requiredRole: 'operario',
  description: 'Catálogo de productos y servicios con configuración dinámica por sector',
  features: [
    'Configuración de campos por sector (panadería, retail, taller)',
    'Importación masiva desde Excel',
    'Gestión de precios e impuestos',
    'Códigos de barras y SKU',
    'Exportación a CSV',
  ],
}
