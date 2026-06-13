export const manifest = {
  id: 'notifications',
  name: 'Notificaciones',
  description: 'Centro de notificaciones y alertas',
  icon: 'bell',
  category: 'integrations',
  url: '/modules/notifications',
  permissions: ['notifications:read', 'notifications:manage'],
  features: [
    'list_notifications',
    'mark_read',
    'archive_notification',
    'unread_count'
  ]
}
