import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'

export default function App() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route path='/' element={<Dashboard />} />
      </Route>
      <Route path='/login' element={<Login />} />
    </Routes>
  )
}
