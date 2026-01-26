export const manifest = {
  id: 'webhooks',
  name: 'Webhooks',
  description: 'Gestión de suscripciones y entregas',
  icon: 'link',
  category: 'integrations',
  url: '/modules/webhooks',
  permissions: ['admin:webhooks'],
  features: [
    'create_subscription',
    'list_subscriptions',
    'test_webhook',
    'manage_deliveries'
  ]
}
