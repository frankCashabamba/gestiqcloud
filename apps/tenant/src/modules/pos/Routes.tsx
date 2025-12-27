/**
 * POS Routes
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import POSView from './POSView'
import DailyCountsView from './components/DailyCountsView'

export default function POSRoutes() {
  return (
    <Routes>
      <Route path="/" element={<POSView />} />
      <Route path="daily-counts" element={<DailyCountsView />} />
    </Routes>
  )
}
