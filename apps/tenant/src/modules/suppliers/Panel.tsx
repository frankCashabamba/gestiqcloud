import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import List from './List'

export default function ProveedoresPanel() {
  return (
    <Routes>
      <Route index element={<List />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
