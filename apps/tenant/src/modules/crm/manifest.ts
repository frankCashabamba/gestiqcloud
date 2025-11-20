import { Users, TrendingUp, Target, Calendar } from 'lucide-react'

export const crmManifest = {
  id: 'crm',
  name: 'CRM',
  description: 'Gestión de relaciones con clientes',
  icon: Users,
  color: '#10B981',
  enabled: true,
  order: 50,
  category: 'ventas',
  routes: [
    {
      path: '/crm',
      component: () => import('./Routes'),
      permissions: ['crm:read'],
    },
  ],
  menu: {
    label: 'CRM',
    icon: Users,
    items: [
      {
        label: 'Dashboard',
        path: '/crm',
        icon: TrendingUp,
        permissions: ['crm:read'],
      },
      {
        label: 'Leads',
        path: '/crm/leads',
        icon: Target,
        permissions: ['crm:leads:read'],
      },
      {
        label: 'Oportunidades',
        path: '/crm/opportunities',
        icon: Calendar,
        permissions: ['crm:opportunities:read'],
      },
      {
        label: 'Pipeline',
        path: '/crm/pipeline',
        icon: TrendingUp,
        permissions: ['crm:pipeline:read'],
      },
    ],
  },
  permissions: [
    'crm:read',
    'crm:write',
    'crm:delete',
    'crm:leads:read',
    'crm:leads:write',
    'crm:opportunities:read',
    'crm:opportunities:write',
    'crm:pipeline:read',
  ],
}

export default crmManifest
