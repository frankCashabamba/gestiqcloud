import React, { useEffect, useState } from 'react'
import tenantApi from '../shared/api/client'

interface Branch {
  id: string
  name: string
  code: string
  is_main: boolean
  is_active: boolean
}

export default function BranchSelector() {
  const [branches, setBranches] = useState<Branch[]>([])
  const [selected, setSelected] = useState<string>(
    localStorage.getItem('selected_branch') || ''
  )
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    tenantApi.get('/api/v1/tenant/branches')
      .then(r => {
        const data = r.data as Branch[]
        setBranches(data)
        if (!selected && data.length > 0) {
          const main = data.find(b => b.is_main) || data[0]
          setSelected(main.id)
          localStorage.setItem('selected_branch', main.id)
        }
      })
      .catch(() => setBranches([]))
      .finally(() => setLoading(false))
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelected(e.target.value)
    localStorage.setItem('selected_branch', e.target.value)
    window.dispatchEvent(new CustomEvent('branch-changed', { detail: e.target.value }))
  }

  if (loading || branches.length <= 1) return null

  return (
    <select
      value={selected}
      onChange={handleChange}
      className="text-sm border border-gray-300 rounded-md px-2 py-1 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      title="Sucursal"
    >
      {branches.map(b => (
        <option key={b.id} value={b.id}>
          {b.name} {b.is_main ? '(Principal)' : ''}
        </option>
      ))}
    </select>
  )
}
