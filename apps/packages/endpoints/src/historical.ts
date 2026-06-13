export const TENANT_HISTORICAL = {
  base: '/api/v1/tenant/historical',
  imports: '/api/v1/tenant/historical/imports',
  importById: (id: string) => `/api/v1/tenant/historical/imports/${id}`,
  upload: '/api/v1/tenant/historical/upload',
  sales: '/api/v1/tenant/historical/sales',
  purchases: '/api/v1/tenant/historical/purchases',
  stock: '/api/v1/tenant/historical/stock',
  dailySales: '/api/v1/tenant/historical/daily-sales',
  dashboard: '/api/v1/tenant/historical/dashboard',
}
