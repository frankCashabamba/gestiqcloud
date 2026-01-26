import React from 'react'
import { Routes, Route } from 'react-router-dom'
import List from './List'
import Detail from './Detail'

export default function CountryPacksRoutes() {
  return (
    <Routes>
      <Route path="/" element={<List />} />
      <Route path=":code" element={<Detail />} />
    </Routes>
  )
}
