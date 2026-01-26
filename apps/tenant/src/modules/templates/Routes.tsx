import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ConfigViewer from './ConfigViewer'

export default function TemplatesRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ConfigViewer />} />
    </Routes>
  )
}
