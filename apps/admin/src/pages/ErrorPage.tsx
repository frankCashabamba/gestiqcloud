import React from 'react'
import { useNavigate, useRouteError } from 'react-router-dom'

export default function ErrorPage() {
  const navigate = useNavigate()
  const err: any = useRouteError?.() || {}
  const message = err?.statusText || err?.message || 'Ha ocurrido un error inesperado'
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow w-full max-w-md text-center">
        <h1 className="text-2xl font-bold mb-2 text-red-600">Error</h1>
        <p className="text-sm text-gray-700 mb-4">{message}</p>
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={()=> navigate(-1)}>Volver</button>
      </div>
    </div>
  )
}

