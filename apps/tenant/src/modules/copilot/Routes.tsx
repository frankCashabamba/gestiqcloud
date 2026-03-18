import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './Dashboard'
import AIMetricsDashboard from './AIMetricsDashboard'

export default function CopilotRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/metrics" element={<AIMetricsDashboard />} />
    </Routes>
  )
}
