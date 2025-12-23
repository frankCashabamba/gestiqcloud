/**
 * ConditionalProductFields
 *
 * Campos de producto que aparecen/desaparecen según la configuración del sector
 *
 * FASE 4 PASO 4: Placeholders dinámicos desde BD
 * - Reemplaza hardcoded placeholders con valores desde template_config
 * - Usa useSectorPlaceholders para cargar dinámicamente
 */
import React from 'react'
import { useTenantFeatures, useTenantSector } from '../contexts/TenantConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../hooks/useSectorPlaceholders'

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
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'products')

  return (
    <>
      {/* ============================================ */}
      {/* CAMPOS DE INVENTARIO CONDICIONALES */}
      {/* ============================================ */}

      {/* Fecha de Caducidad (solo panadería, alimentos) */}
      {features.inventory_expiry_tracking && (
        <div className="form-field">
          <label htmlFor="expires_at" className="form-label">
            Fecha de Caducidad {features.inventory_expiry_tracking && '*'}
          </label>
          <input
            type="date"
            id="expires_at"
            name="expires_at"
            value={formData.expires_at || ''}
            onChange={onChange}
            min={new Date().toISOString().split('T')[0]}
            required={features.inventory_expiry_tracking}
            className="form-input"
          />
          {features.inventory_expiry_tracking && (
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
            Número de Lote
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'lote', 'Número de lote')}
            className="form-input"
          />
          <small className="form-help">
            Identifica el lote de producción
          </small>
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
            placeholder={getFieldPlaceholder(placeholders, 'numero_serie', 'Ej: SN-123456789')}
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
