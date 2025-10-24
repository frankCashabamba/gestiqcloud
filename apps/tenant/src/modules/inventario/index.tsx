/**
 * Inventario Module
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import StockList from './StockList'
import StockMovesList from './StockMovesList'
import AdjustmentForm from './AdjustmentForm'

export default function InventarioModule() {
  return (
    <Routes>
      <Route path="/" element={<StockList />} />
      <Route path="/movimientos" element={<StockMovesList />} />
      <Route path="/ajustes" element={<AdjustmentForm />} />
    </Routes>
  )
}
