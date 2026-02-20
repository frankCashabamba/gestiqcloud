import React from 'react'
import { Routes, Route } from 'react-router-dom'
import NotificationCenter from './NotificationCenter'

export default function NotificationsRoutes() {
  return (
    <Routes>
      <Route path="/" element={<NotificationCenter />} />
    </Routes>
  )
}
