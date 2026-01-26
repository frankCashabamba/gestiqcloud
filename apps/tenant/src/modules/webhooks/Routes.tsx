import React from 'react'
import { Routes, Route } from 'react-router-dom'
import SubscriptionsList from './SubscriptionsList'

export default function WebhooksRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SubscriptionsList />} />
    </Routes>
  )
}
