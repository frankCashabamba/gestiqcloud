import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './Dashboard'

export default function CopilotRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
    </Routes>
  )
}
