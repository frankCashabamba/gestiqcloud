import React from 'react'

const QuotesList = React.lazy(() => import('./QuotesList'))
const QuoteForm = React.lazy(() => import('./QuoteForm'))
const QuoteDetail = React.lazy(() => import('./QuoteDetail'))

export const manifest = {
  id: 'quotes',
  name: 'Presupuestos',
  version: '1.0.0',
  enabled: true,
  permissions: ['quotes.manage'],
  routes: [
    { path: '/quotes', element: QuotesList },
    { path: '/quotes/new', element: QuoteForm },
    { path: '/quotes/:id', element: QuoteDetail },
    { path: '/quotes/:id/edit', element: QuoteForm },
  ],
  menu: {
    title: 'Presupuestos',
    icon: '📝',
    route: '/quotes',
    order: 17,
  },
}
