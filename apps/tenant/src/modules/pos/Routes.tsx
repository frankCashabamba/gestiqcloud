/**
 * POS Routes
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import POSView from './POSView'

export default function POSRoutes() {
  return (
    <Routes>
      <Route path="/" element={<POSView />} />
    </Routes>
  )
}
