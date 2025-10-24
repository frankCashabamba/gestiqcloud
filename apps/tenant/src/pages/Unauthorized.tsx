import React from 'react'

export default function Unauthorized() {
  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', padding: 16 }}>
      <h1 style={{ marginTop: 0 }}>Acceso no autorizado</h1>
      <p>No tienes acceso al módulo solicitado. Si crees que es un error, contacta con el administrador.</p>
    </div>
  )
}

