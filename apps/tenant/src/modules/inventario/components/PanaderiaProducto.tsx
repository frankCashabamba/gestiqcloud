import React, { useState } from 'react'

type Ingrediente = { name: string; cantidad: string; unidad: string }

export default function PanaderiaProducto() {
  const [nombre, setNombre] = useState('')
  const [precio, setPrecio] = useState('')
  const [stock, setStock] = useState('')
  const [rinde, setRinde] = useState('')
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([{ name: '', cantidad: '', unidad: '' }])

  const onIngChange = (i: number, field: keyof Ingrediente, val: string) => {
    setIngredientes(prev => prev.map((ing, idx) => idx===i ? { ...ing, [field]: val } as Ingrediente : ing))
  }
  const addIng = () => setIngredientes(prev => [...prev, { name: '', cantidad: '', unidad: '' }])

  const calcularCosto = () => {
    alert('Cálculo de costo pendiente')
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-2">Nuevo producto (Panadería)</h2>
      <div className="space-y-2" style={{ maxWidth: 640 }}>
        <input placeholder="Nombre del producto" value={nombre} onChange={(e)=> setNombre(e.target.value)} className="border p-2 w-full" />
        <input placeholder="Precio de venta" value={precio} onChange={(e)=> setPrecio(e.target.value)} className="border p-2 w-full" />
        <input placeholder="Stock inicial" value={stock} onChange={(e)=> setStock(e.target.value)} className="border p-2 w-full" />
        <input placeholder="Cantidad que rinde la receta (ej. 100 panes)" value={rinde} onChange={(e)=> setRinde(e.target.value)} className="border p-2 w-full" />

        <h3 className="text-lg mt-4">Ingredientes</h3>
        {ingredientes.map((ing, idx) => (
          <div key={idx} className="flex gap-2 my-1">
            <input placeholder="Ingrediente" value={ing.name} onChange={(e)=> onIngChange(idx, 'name', e.target.value)} className="border p-1 flex-1" />
            <input placeholder="Cantidad" value={ing.cantidad} onChange={(e)=> onIngChange(idx, 'cantidad', e.target.value)} className="border p-1 w-20" />
            <input placeholder="Unidad (g, kg, L)" value={ing.unidad} onChange={(e)=> onIngChange(idx, 'unidad', e.target.value)} className="border p-1 w-24" />
          </div>
        ))}
        <button onClick={addIng} className="bg-blue-500 text-white p-2 mt-2">+ Agregar Ingrediente</button>
        <button onClick={calcularCosto} className="bg-green-600 text-white p-2 mt-4">Calcular Costo</button>
      </div>
    </div>
  )
}
