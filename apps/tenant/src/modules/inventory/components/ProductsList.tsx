// apps/tenant/src/modules/inventario/components/ProductosList.tsx (UTF-8)
import React, { useEffect, useState } from 'react'
import { fetchProductos, updateProducto } from '../services/inventory'
import { ensureArray } from '../../../shared/utils/array'
import { getCompanySettings, getCurrencySymbol } from '../../../services/companySettings'
import type { Producto } from '../types/producto'
import { INVENTORY_DEFAULTS } from '../../../constants/defaults'

export default function ProductosList() {
    const [items, setItems] = useState<Producto[]>([])
    const [loading, setLoading] = useState(true)
    const [q, setQ] = useState('')
    const [editingId, setEditingId] = useState<string | number | null>(null)
    const [editData, setEditData] = useState<any>({})
    const [categoryFilter, setCategoryFilter] = useState<string>('')
    const [currencySymbol, setCurrencySymbol] = useState(INVENTORY_DEFAULTS.CURRENCY_SYMBOL)

    useEffect(() => {
        loadProducts()
        getCompanySettings().then((config) => setCurrencySymbol(getCurrencySymbol(config)))
    }, [])

    const loadProducts = async () => {
        try {
            const d = await fetchProductos()
            setItems(ensureArray<Producto>(d))
        } catch (error) {
            console.error('Error cargando productos:', error)
        } finally {
            setLoading(false)
        }
    }

    const base = Array.isArray(items) ? items : []
    const filtered = base.filter((p) => {
        const ql = q.toLowerCase()
        const matchSearch = (p.name || '').toLowerCase().includes(ql) || (p.sku || '').toLowerCase().includes(ql)
        const matchCategory = !categoryFilter || p.categoria === categoryFilter
        return matchSearch && matchCategory
    })

    const categories = Array.from(new Set(base.map((p) => p.categoria).filter(Boolean)))

    const startEdit = (product: Producto) => {
        setEditingId(product.id)
        setEditData({
            name: product.name,
            price: product.price,
            stock: product.stock,
            categoria: product.categoria || '',
            sku: product.sku || '',
        })
    }

    const cancelEdit = () => {
        setEditingId(null)
        setEditData({})
    }

    const saveEdit = async (id: string | number) => {
        try {
            await updateProducto(String(id), editData)
            setItems(items.map((p) => (p.id === id ? { ...p, ...editData } : p)))
            setEditingId(null)
            setEditData({})
        } catch (error) {
            console.error('Error actualizando producto:', error)
            alert('Error saving changes')
        }
    }

    if (loading) {
        return (
            <div className="p-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-4" />
                    <div className="h-10 bg-gray-200 rounded w-full mb-4" />
                    <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-16 bg-gray-200 rounded" />
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Product Management</h2>

                <div className="flex gap-3 mb-4">
                    <input
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                        placeholder="Search by name or code..."
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />

                    <select
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All categories</option>
                        {categories.map((cat) => (
                            <option key={cat} value={cat}>
                                {cat}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="text-sm text-gray-600">Showing {filtered.length} of {base.length} products</div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Code</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {filtered.map((p) => (
                            <tr key={p.id} className={`hover:bg-gray-50 ${editingId === p.id ? 'bg-blue-50' : ''}`}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {editingId === p.id ? (
                                        <input
                                            type="text"
                                            value={editData.sku}
                                            onChange={(e) => setEditData({ ...editData, sku: e.target.value })}
                                            className="px-2 py-1 border rounded w-full"
                                        />
                                    ) : (
                                        <span className="text-sm font-mono text-gray-900">{p.sku}</span>
                                    )}
                                </td>

                                <td className="px-6 py-4">
                                    {editingId === p.id ? (
                                        <input
                                            type="text"
                                            value={editData.name}
                                            onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                                            className="px-2 py-1 border rounded w-full"
                                        />
                                    ) : (
                                        <span className="text-sm font-medium text-gray-900">{p.name}</span>
                                    )}
                                </td>

                                <td className="px-6 py-4 whitespace-nowrap">
                                    {editingId === p.id ? (
                                        <select
                                            value={editData.categoria}
                                            onChange={(e) => setEditData({ ...editData, categoria: e.target.value })}
                                            className="px-2 py-1 border rounded w-full"
                                        >
                                            <option value="">No category</option>
                                            <option value="Panadería">Panadería</option>
                                            <option value="Pastelería">Pastelería</option>
                                            <option value="Bollería">Bollería</option>
                                            <option value="Bebidas">Bebidas</option>
                                            <option value="Otros">Otros</option>
                                        </select>
                                    ) : (
                                        <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                            {p.categoria || 'No category'}
                                        </span>
                                    )}
                                </td>

                                <td className="px-6 py-4 whitespace-nowrap">
                                    {editingId === p.id ? (
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={editData.price}
                                            onChange={(e) => setEditData({ ...editData, price: parseFloat(e.target.value) })}
                                            className="px-2 py-1 border rounded w-24"
                                        />
                                    ) : (
                                        <span className="text-sm font-bold text-gray-900">{currencySymbol}{(p.price || 0).toFixed(2)}</span>
                                    )}
                                </td>

                                <td className="px-6 py-4 whitespace-nowrap">
                                    {editingId === p.id ? (
                                        <input
                                            type="number"
                                            value={editData.stock}
                                            onChange={(e) => setEditData({ ...editData, stock: parseFloat(e.target.value) })}
                                            className="px-2 py-1 border rounded w-24"
                                        />
                                    ) : (
                                        <span className={`text-sm font-medium ${(p.stock || 0) < 10 ? 'text-red-600' : 'text-gray-900'}`}>{p.stock || 0}</span>
                                    )}
                                </td>

                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                    {editingId === p.id ? (
                                        <div className="flex gap-2">
                                            <button onClick={() => saveEdit(p.id)} className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700">Save</button>
                                            <button onClick={cancelEdit} className="px-3 py-1 bg-gray-400 text-white rounded hover:bg-gray-500">Cancel</button>
                                        </div>
                                    ) : (
                                        <button onClick={() => startEdit(p)} className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">Edit</button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {filtered.length === 0 && (
                    <div className="text-center py-12">
                        <p className="text-gray-500 text-lg">No products found</p>
                        <p className="text-gray-400 text-sm mt-2">Try a different search term</p>
                    </div>
                )}
            </div>
        </div>
    )
}
