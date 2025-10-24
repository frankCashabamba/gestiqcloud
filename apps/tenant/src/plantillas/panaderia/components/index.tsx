/**
 * Panadería Module - SPEC-1 Integration
 * Módulo completo para gestión de panadería profesional
 */
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import DailyInventoryList from './DailyInventoryList'
import ExcelImporter from './ExcelImporter'
import PurchaseList from './PurchaseList'
import MilkRecordList from './MilkRecordList'
import Dashboard from './Dashboard'

export default function PanaderiaModule() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/inventario" element={<DailyInventoryList />} />
      <Route path="/compras" element={<PurchaseList />} />
      <Route path="/leche" element={<MilkRecordList />} />
      <Route path="/importador" element={<ExcelImporter />} />
    </Routes>
  )
}
