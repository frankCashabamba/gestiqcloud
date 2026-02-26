import React from 'react'

import { Routes, Route } from 'react-router-dom'

import Detail from './Detail'
import List from './List'

export default function CountryPacksRoutes() {
  return (
    <Routes>
      <Route path="/" element={<List />} />
      <Route path=":code" element={<Detail />} />
    </Routes>
  )
}
