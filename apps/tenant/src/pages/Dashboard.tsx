import React from 'react'
import { useAuth } from '../auth/AuthContext'

export default function Dashboard() {
  const { profile, logout, brand } = useAuth()
  return (
    <div>
      <div className='header'>
        <h2>{brand} — Panel</h2>
        <button onClick={logout}>Cerrar sesión</button>
      </div>
      <div style={{maxWidth: '960px', margin:'1rem auto'}}>
        <pre>{JSON.stringify(profile, null, 2)}</pre>
      </div>
    </div>
  )
}
