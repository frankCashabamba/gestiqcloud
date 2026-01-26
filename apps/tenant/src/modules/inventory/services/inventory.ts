export * from './inventario'

// Stubbed alert functions until backend endpoints exist
export const listStockAlerts = async () => []
export const updateReorderPoint = async (_id: string, _data: any) => {}
export const resolveAlert = async (_id: string) => {}
export const configureNotificationChannel = async (_channel?: any, _payload?: any) => {}
export const testNotification = async (_channelId?: string, _payload?: any) => {}
