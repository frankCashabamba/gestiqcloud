export type StockAlert = {
  id: string
  producto_id: string
  producto_nombre: string
  producto_sku: string
  stock_actual: number
  stock_minimo: number
  estado: 'pending' | 'resolved' | 'ignored'
  ultima_notificacion?: string
  created_at: string
}

export type NotificationChannel = 'email' | 'whatsapp' | 'telegram'

export type NotificationChannelConfig = {
  tipo: NotificationChannel
  enabled: boolean
  config: {
    // Email
    email?: string
    
    // WhatsApp
    phone?: string
    provider?: 'twilio' | 'infobip'
    api_key?: string
    
    // Telegram
    chat_id?: string
    bot_token?: string
  }
}

export type ReorderPointUpdate = {
  producto_id: string
  stock_minimo: number
}
