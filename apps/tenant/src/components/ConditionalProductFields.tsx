/**
 * ConditionalProductFields
 *
 * Campos de producto que aparecen/desaparecen según la configuración del sector
 */
import React from 'react'
import { useTenantFeatures, useTenantSector } from '../contexts/TenantConfigContext'

interface ConditionalProductFieldsProps {
  formData: any
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  onCheckboxChange?: (name: string, checked: boolean) => void
}

export function ConditionalProductFields({
  formData,
  onChange,
  onCheckboxChange
}: ConditionalProductFieldsProps) {
  const features = useTenantFeatures()
  const sector = useTenantSector()

  return (
    <>
      {/* ============================================ */}
      {/* CAMPOS DE INVENTARIO CONDICIONALES */}
      {/* ============================================ */}

      {/* Fecha de Caducidad (solo panadería, alimentos) */}
      {features.inventory_expiry_tracking && (
        <div className="form-field">
          <label htmlFor="expires_at" className="form-label">
            Fecha de Caducidad {sector.is_panaderia && '*'}
          </label>
          <input
            type="date"
            id="expires_at"
            name="expires_at"
            value={formData.expires_at || ''}
            onChange={onChange}
            min={new Date().toISOString().split('T')[0]}
            required={sector.is_panaderia}
            className="form-input"
          />
          {sector.is_panaderia && (
            <small className="form-help">
              Productos perecederos requieren fecha de caducidad
            </small>
          )}
        </div>
      )}

      {/* Lote/Hornada (panadería, taller) */}
      {features.inventory_lot_tracking && (
        <div className="form-field">
          <label htmlFor="lot" className="form-label">
            {sector.is_panaderia ? 'Lote/Hornada' :
             sector.is_taller ? 'Lote de Fabricación' :
             'Número de Lote'}
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={
              sector.is_panaderia ? 'Ej: H-2025-001' :
              sector.is_taller ? 'Ej: LOT-ABC-123' :
              'Número de lote'
            }
            className="form-input"
          />
          {sector.is_panaderia && (
            <small className="form-help">
              Identifica la hornada de producción
            </small>
          )}
        </div>
      )}

      {/* Número de Serie (taller, retail electrónicos) */}
      {features.inventory_serial_tracking && (
        <div className="form-field">
          <label htmlFor="serial_number" className="form-label">
            Número de Serie
          </label>
          <input
            type="text"
            id="serial_number"
            name="serial_number"
            value={formData.serial_number || ''}
            onChange={onChange}
            placeholder="Ej: SN-123456789"
            className="form-input"
          />
          <small className="form-help">
            Para tracking individual de repuestos/productos
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* CAMPOS DE POS CONDICIONALES */}
      {/* ============================================ */}

      {/* Venta por Peso (panadería) */}
      {features.pos_enable_weights && (
        <>
          <div className="form-field">
            <label className="form-checkbox">
              <input
                type="checkbox"
                name="sold_by_weight"
                checked={formData.sold_by_weight || false}
                onChange={(e) => onCheckboxChange?.('sold_by_weight', e.target.checked)}
              />
              <span>Se vende por peso</span>
            </label>
          </div>

          {formData.sold_by_weight && (
            <div className="form-field">
              <label htmlFor="weight_unit" className="form-label">
                Unidad de Peso *
              </label>
              <select
                id="weight_unit"
                name="weight_unit"
                value={formData.weight_unit || 'kg'}
                onChange={onChange}
                required
                className="form-input"
              >
                <option value="kg">Kilogramos (kg)</option>
                <option value="g">Gramos (g)</option>
                <option value="lb">Libras (lb)</option>
              </select>
            </div>
          )}
        </>
      )}

      {/* ============================================ */}
      {/* CAMPOS ESPECÍFICOS POR SECTOR */}
      {/* ============================================ */}

      {/* PANADERÍA */}
      {sector.is_panaderia && (
        <>
          <div className="form-field">
            <label htmlFor="temperatura_horneado" className="form-label">
              Temperatura de Horneado (°C)
            </label>
            <input
              type="number"
              id="temperatura_horneado"
              name="temperatura_horneado"
              value={formData.temperatura_horneado || ''}
              onChange={onChange}
              placeholder="180"
              min="0"
              max="300"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="tipo_masa" className="form-label">
              Tipo de Masa
            </label>
            <select
              id="tipo_masa"
              name="tipo_masa"
              value={formData.tipo_masa || ''}
              onChange={onChange}
              className="form-input"
            >
              <option value="">-- Seleccionar --</option>
              <option value="masa_madre">Masa Madre</option>
              <option value="levadura">Masa de Levadura</option>
              <option value="quebrada">Masa Quebrada</option>
              <option value="hojaldre">Hojaldre</option>
              <option value="fermentada">Masa Fermentada</option>
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="tiempo_fermentacion" className="form-label">
              Tiempo de Fermentación (horas)
            </label>
            <input
              type="number"
              id="tiempo_fermentacion"
              name="tiempo_fermentacion"
              value={formData.tiempo_fermentacion || ''}
              onChange={onChange}
              placeholder="2"
              min="0"
              max="72"
              step="0.5"
              className="form-input"
            />
          </div>
        </>
      )}

      {/* TALLER MECÁNICO */}
      {sector.is_taller && (
        <>
          <div className="form-field">
            <label htmlFor="codigo_oem" className="form-label">
              Código OEM
            </label>
            <input
              type="text"
              id="codigo_oem"
              name="codigo_oem"
              value={formData.codigo_oem || ''}
              onChange={onChange}
              placeholder="Código del fabricante"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="marca_vehiculo" className="form-label">
              Marca de Vehículo Compatible
            </label>
            <input
              type="text"
              id="marca_vehiculo"
              name="marca_vehiculo"
              value={formData.marca_vehiculo || ''}
              onChange={onChange}
              placeholder="Ej: Toyota, Ford, Volkswagen"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="modelo_compatible" className="form-label">
              Modelo Compatible
            </label>
            <input
              type="text"
              id="modelo_compatible"
              name="modelo_compatible"
              value={formData.modelo_compatible || ''}
              onChange={onChange}
              placeholder="Ej: Corolla, Focus, Golf"
              className="form-input"
            />
          </div>

          <div className="form-row">
            <div className="form-field">
              <label htmlFor="año_desde" className="form-label">
                Año Desde
              </label>
              <input
                type="number"
                id="año_desde"
                name="año_desde"
                value={formData.año_desde || ''}
                onChange={onChange}
                placeholder="2015"
                min="1950"
                max={new Date().getFullYear() + 1}
                className="form-input"
              />
            </div>

            <div className="form-field">
              <label htmlFor="año_hasta" className="form-label">
                Año Hasta
              </label>
              <input
                type="number"
                id="año_hasta"
                name="año_hasta"
                value={formData.año_hasta || ''}
                onChange={onChange}
                placeholder="2024"
                min="1950"
                max={new Date().getFullYear() + 1}
                className="form-input"
              />
            </div>
          </div>
        </>
      )}

      {/* RETAIL */}
      {sector.is_retail && (
        <>
          <div className="form-field">
            <label htmlFor="marca" className="form-label">
              Marca
            </label>
            <input
              type="text"
              id="marca"
              name="marca"
              value={formData.marca || ''}
              onChange={onChange}
              placeholder="Marca del producto"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="modelo" className="form-label">
              Modelo
            </label>
            <input
              type="text"
              id="modelo"
              name="modelo"
              value={formData.modelo || ''}
              onChange={onChange}
              placeholder="Modelo/Referencia"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="color" className="form-label">
              Color/Variante
            </label>
            <input
              type="text"
              id="color"
              name="color"
              value={formData.color || ''}
              onChange={onChange}
              placeholder="Ej: Negro, Azul, Rojo"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="talla" className="form-label">
              Talla/Tamaño
            </label>
            <input
              type="text"
              id="talla"
              name="talla"
              value={formData.talla || ''}
              onChange={onChange}
              placeholder="Ej: M, L, XL, 42"
              className="form-input"
            />
          </div>
        </>
      )}

      <style>{`
        .form-field {
          margin-bottom: 16px;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .form-label {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 6px;
        }

        .form-input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
        }

        .form-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .form-checkbox {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .form-checkbox input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
        }

        .form-help {
          display: block;
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }
      `}</style>
    </>
  )
}

export default ConditionalProductFields
