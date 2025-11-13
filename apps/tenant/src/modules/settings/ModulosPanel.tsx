import React, { useState, useEffect } from 'react'
import ModuleCard from './components/ModuleCard'
import ModuleConfigForm from './components/ModuleConfigForm'
import { useToast, getErrorMessage } from '../../shared/toast'

interface Module {
  id: string
  name: string
  icon: string
  description: string
  category: string
  enabled: boolean
  config?: any
  dependencies?: string[]
}

// Definición de módulos disponibles
const AVAILABLE_MODULES: Module[] = [
  // VENTAS
  { id: 'pos', name: 'Punto de Venta (TPV)', icon: '🛒', description: 'Sistema de caja y ventas al mostrador', category: 'Ventas', enabled: true },
  { id: 'invoicing', name: 'Facturación', icon: '📄', description: 'Gestión de facturas, presupuestos y albaranes', category: 'Ventas', enabled: true },
  { id: 'einvoicing', name: 'Factura Electrónica', icon: '⚡', description: 'Envío automático a SRI/AEAT', category: 'Ventas', enabled: false, dependencies: ['invoicing'] },
  { id: 'crm', name: 'CRM', icon: '👥', description: 'Gestión de clientes y oportunidades', category: 'Ventas', enabled: true },
  
  // COMPRAS
  { id: 'purchases', name: 'Compras', icon: '📦', description: 'Órdenes de compra y proveedores', category: 'Compras', enabled: true },
  { id: 'expenses', name: 'Gastos', icon: '💳', description: 'Control de gastos y justificantes', category: 'Compras', enabled: true },
  
  // OPERACIONES
  { id: 'inventory', name: 'Inventario', icon: '📊', description: 'Control de stock, lotes y almacenes', category: 'Operaciones', enabled: true },
  { id: 'imports', name: 'Importaciones', icon: '📥', description: 'Carga masiva de productos y catálogos', category: 'Operaciones', enabled: true },
  { id: 'warehouse', name: 'Almacenes', icon: '🏭', description: 'Gestión multi-almacén', category: 'Operaciones', enabled: false, dependencies: ['inventory'] },
  
  // FINANZAS
  { id: 'accounting', name: 'Contabilidad', icon: '💰', description: 'Libro mayor y balance', category: 'Finanzas', enabled: false },
  { id: 'payments', name: 'Pagos Online', icon: '💳', description: 'Stripe, Kushki, PayPhone', category: 'Finanzas', enabled: true },
  { id: 'banking', name: 'Conciliación Bancaria', icon: '🏦', description: 'Sincronización con bancos', category: 'Finanzas', enabled: false },
  
  // RRHH
  { id: 'hr', name: 'Recursos Humanos', icon: '👔', description: 'Empleados, nóminas, vacaciones', category: 'RRHH', enabled: false },
  { id: 'attendance', name: 'Control Horario', icon: '⏰', description: 'Fichajes y turnos', category: 'RRHH', enabled: false },
  
  // MARKETING
  { id: 'campaigns', name: 'Campañas', icon: '📧', description: 'Email marketing y promociones', category: 'Marketing', enabled: false },
  { id: 'loyalty', name: 'Fidelización', icon: '🎁', description: 'Programas de puntos y descuentos', category: 'Marketing', enabled: false },
]

export default function ModulosPanel() {
  const [modules, setModules] = useState<Module[]>(AVAILABLE_MODULES)
  const [selectedModule, setSelectedModule] = useState<Module | null>(null)
  const [activeTab, setActiveTab] = useState<string>('Todos')
  const { success, error, warning } = useToast()

  // Categorías únicas
  const categories = ['Todos', ...Array.from(new Set(modules.map(m => m.category)))]

  // Filtrar módulos por categoría
  const filteredModules = activeTab === 'Todos' 
    ? modules 
    : modules.filter(m => m.category === activeTab)

  // Cargar estado de módulos desde localStorage
  useEffect(() => {
    const saved = localStorage.getItem('tenant_modules_config')
    if (saved) {
      try {
        const config = JSON.parse(saved)
        setModules(prev => prev.map(m => ({
          ...m,
          enabled: config[m.id]?.enabled ?? m.enabled,
          config: config[m.id]?.config ?? m.config
        })))
      } catch (e) {
        console.error('Error loading modules config', e)
      }
    }
  }, [])

  // Guardar configuración
  const saveModulesConfig = (updatedModules: Module[]) => {
    const config: any = {}
    updatedModules.forEach(m => {
      config[m.id] = { enabled: m.enabled, config: m.config }
    })
    localStorage.setItem('tenant_modules_config', JSON.stringify(config))
  }

  // Toggle módulo
  const handleToggle = async (moduleId: string, enabled: boolean) => {
    const module = modules.find(m => m.id === moduleId)
    if (!module) return

    // Verificar dependencias si se está desactivando
    if (!enabled && module.enabled) {
      const dependents = modules.filter(m => 
        m.enabled && m.dependencies?.includes(moduleId)
      )
      if (dependents.length > 0) {
        warning(`No se puede desactivar. Los siguientes módulos dependen de él: ${dependents.map(d => d.name).join(', ')}`)
        return
      }

      // Confirmación antes de desactivar
      if (!confirm(`¿Desactivar módulo ${module.name}?`)) {
        return
      }
    }

    // Verificar dependencias si se está activando
    if (enabled && !module.enabled && module.dependencies) {
      const missingDeps = module.dependencies.filter(depId => {
        const dep = modules.find(m => m.id === depId)
        return !dep?.enabled
      })
      if (missingDeps.length > 0) {
        const depNames = missingDeps
          .map(depId => modules.find(m => m.id === depId)?.name)
          .filter(Boolean)
        warning(`Primero debes activar: ${depNames.join(', ')}`)
        return
      }
    }

    const updated = modules.map(m => 
      m.id === moduleId ? { ...m, enabled } : m
    )
    setModules(updated)
    saveModulesConfig(updated)
    success(`Módulo ${module.name} ${enabled ? 'activado' : 'desactivado'}`)
  }

  // Abrir configuración
  const handleClickModule = (moduleId: string) => {
    const module = modules.find(m => m.id === moduleId)
    if (module) {
      setSelectedModule(module)
    }
  }

  // Guardar configuración de módulo
  const handleSaveConfig = async (moduleId: string, config: any) => {
    const updated = modules.map(m => 
      m.id === moduleId ? { ...m, config } : m
    )
    setModules(updated)
    saveModulesConfig(updated)
  }

  const activeCount = modules.filter(m => m.enabled).length
  const totalCount = modules.length

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Módulos del Sistema
        </h1>
        <p className="text-gray-600">
          Activa o desactiva módulos según las necesidades de tu negocio
        </p>
        <div className="mt-4 inline-block bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-semibold">
          {activeCount} de {totalCount} módulos activos
        </div>
      </div>

      {/* Tabs de Categorías */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-1 overflow-x-auto">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveTab(cat)}
              className={`
                px-4 py-2 font-medium transition-colors whitespace-nowrap
                ${activeTab === cat
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
                }
              `}
            >
              {cat}
              {cat !== 'Todos' && (
                <span className="ml-2 text-xs bg-gray-200 px-2 py-1 rounded-full">
                  {modules.filter(m => m.category === cat && m.enabled).length}/
                  {modules.filter(m => m.category === cat).length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Grid de Módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredModules.map(module => (
          <ModuleCard
            key={module.id}
            module={module}
            onToggle={handleToggle}
            onClick={handleClickModule}
          />
        ))}
      </div>

      {filteredModules.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No hay módulos en esta categoría</p>
        </div>
      )}

      {/* Modal de Configuración */}
      {selectedModule && (
        <ModuleConfigForm
          moduleId={selectedModule.id}
          moduleName={selectedModule.name}
          config={selectedModule.config || {}}
          onSave={handleSaveConfig}
          onClose={() => setSelectedModule(null)}
        />
      )}

      {/* Ayuda */}
      <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-semibold text-yellow-800 mb-2">💡 Consejos</h3>
        <ul className="text-sm text-yellow-700 space-y-1 list-disc pl-5">
          <li>Haz clic en cualquier tarjeta para configurar el módulo</li>
          <li>Los módulos desactivados no aparecerán en el menú principal</li>
          <li>Algunos módulos requieren que otros estén activos (dependencias)</li>
          <li>La configuración se guarda automáticamente</li>
        </ul>
      </div>
    </div>
  )
}
