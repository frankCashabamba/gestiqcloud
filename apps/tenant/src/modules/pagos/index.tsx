/**
 * Pagos Module - Pagos online
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import PaymentLinkGenerator from './PaymentLinkGenerator'
import PaymentsList from './PaymentsList'

export default function PagosModule() {
  return (
    <Routes>
      <Route path="/" element={<PaymentsList />} />
      <Route path="/nuevo-link" element={<PaymentLinkGenerator />} />
    </Routes>
  )
}
