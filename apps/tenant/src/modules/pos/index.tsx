/**
 * POS Module - Point of Sale
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './Dashboard'
import TicketCreator from './TicketCreator'
import ShiftManager from './ShiftManager'
import ReceiptHistory from './ReceiptHistory'

export default function POSModule() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/nuevo-ticket" element={<TicketCreator />} />
      <Route path="/turnos" element={<ShiftManager />} />
      <Route path="/historial" element={<ReceiptHistory />} />
    </Routes>
  )
}
