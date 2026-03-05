import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

type Ingrediente = { name: string; cantidad: string; unidad: string }

export default function PanaderiaProducto() {
  const { t } = useTranslation(['inventory', 'common'])
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
    alert(t('inventory:bakery.costPending'))
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-2">{t('inventory:bakery.title')}</h2>
      <div className="space-y-2" style={{ maxWidth: 640 }}>
        <input placeholder={t('inventory:bakery.productName')} value={nombre} onChange={(e)=> setNombre(e.target.value)} className="border p-2 w-full" />
        <input placeholder={t('inventory:bakery.salePrice')} value={precio} onChange={(e)=> setPrecio(e.target.value)} className="border p-2 w-full" />
        <input placeholder={t('inventory:bakery.initialStock')} value={stock} onChange={(e)=> setStock(e.target.value)} className="border p-2 w-full" />
        <input placeholder={t('inventory:bakery.recipeYield')} value={rinde} onChange={(e)=> setRinde(e.target.value)} className="border p-2 w-full" />

        <h3 className="text-lg mt-4">{t('inventory:bakery.ingredients')}</h3>
        {ingredientes.map((ing, idx) => (
          <div key={idx} className="flex gap-2 my-1">
            <input placeholder={t('inventory:bakery.ingredientName')} value={ing.name} onChange={(e)=> onIngChange(idx, 'name', e.target.value)} className="border p-1 flex-1" />
            <input placeholder={t('inventory:bakery.quantity')} value={ing.cantidad} onChange={(e)=> onIngChange(idx, 'cantidad', e.target.value)} className="border p-1 w-20" />
            <input placeholder={t('inventory:bakery.unitPlaceholder')} value={ing.unidad} onChange={(e)=> onIngChange(idx, 'unidad', e.target.value)} className="border p-1 w-24" />
          </div>
        ))}
        <button onClick={addIng} className="bg-blue-500 text-white p-2 mt-2">{t('inventory:bakery.addIngredient')}</button>
        <button onClick={calcularCosto} className="bg-green-600 text-white p-2 mt-4">{t('inventory:bakery.calculateCost')}</button>
      </div>
    </div>
  )
}
