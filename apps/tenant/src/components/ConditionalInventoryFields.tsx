/**
 * ConditionalInventoryFields
 *
 * Campos de movimiento de inventario que aparecen según configuración del sector
 * Similar a ConditionalProductFields pero para stock movements
 */
import React from 'react'
import { useTenantFeatures, useTenantSector } from '../contexts/TenantConfigContext'

interface ConditionalInventoryFieldsProps {
  formData: any
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  moveType?: 'in' | 'out' | 'adjustment' | 'transfer'
}

export function ConditionalInventoryFields({
  formData,
  onChange,
  moveType = 'in'
}: ConditionalInventoryFieldsProps) {
  const features = useTenantFeatures()
  const sector = useTenantSector()

  const isIncoming = moveType === 'in' || moveType === 'adjustment'

  return (
    <>
      {/* ============================================ */}
      {/* FECHA DE CADUCIDAD (Panadería, Alimentos) */}
      {/* ============================================ */}

      {features.inventory_expiry_tracking && isIncoming && (
        <div className="inventory-field">
          <label htmlFor="expires_at" className="field-label">
            Fecha de Caducidad {sector.is_panaderia && '*'}
            <span className="label-badge expiry">
              {sector.is_panaderia ? '🥐 Requerido' : 'Opcional'}
            </span>
          </label>
          <input
            type="date"
            id="expires_at"
            name="expires_at"
            value={formData.expires_at || ''}
            onChange={onChange}
            min={new Date().toISOString().split('T')[0]}
            required={sector.is_panaderia}
            className="field-input"
            aria-label="Fecha de caducidad del producto"
          />
          {sector.is_panaderia && (
            <small className="field-help warning">
              ⚠️ Productos perecederos requieren fecha de caducidad obligatoria
            </small>
          )}
        </div>
      )}

      {/* ============================================ */}
      {/* LOTE / HORNADA */}
      {/* ============================================ */}

      {features.inventory_lot_tracking && isIncoming && (
        <div className="inventory-field">
          <label htmlFor="lot" className="field-label">
            {sector.is_panaderia ? '🥐 Lote/Hornada' :
             sector.is_taller ? '🔧 Lote de Fabricación' :
             '📦 Número de Lote'}
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={
              sector.is_panaderia ? 'Ej: H-2025-028' :
              sector.is_taller ? 'Ej: LOT-BRK-2025-001' :
              'Número de lote'
            }
            className="field-input"
            aria-label="Número de lote o hornada"
          />
          {sector.is_panaderia && (
            <small className="field-help">
              Identifica la hornada de producción (formato sugerido: H-AÑO-NNN)
            </small>
          )}
          {sector.is_taller && (
            <small className="field-help">
              Lote del fabricante para trazabilidad de repuestos
            </small>
          )}
        </div>
      )}

      {/* ============================================ */}
      {/* NÚMERO DE SERIE (Taller, Retail Electrónicos) */}
      {/* ============================================ */}

      {features.inventory_serial_tracking && (
        <div className="inventory-field">
          <label htmlFor="serial_number" className="field-label">
            {sector.is_taller ? '🔧 Número de Serie' : '📱 Número de Serie'}
            {sector.is_taller && <span className="label-badge serial">Repuestos</span>}
          </label>
          <input
            type="text"
            id="serial_number"
            name="serial_number"
            value={formData.serial_number || ''}
            onChange={onChange}
            placeholder={
              sector.is_taller
                ? 'Ej: SN-ALT-123456789'
                : 'Ej: SN-123456789'
            }
            className="field-input"
            aria-label="Número de serie para tracking individual"
          />
          <small className="field-help">
            {sector.is_taller
              ? 'Permite tracking individual de repuestos garantizados'
              : 'Para seguimiento individual del producto'}
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* UBICACIÓN EN ALMACÉN */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="location" className="field-label">
          Ubicación en Almacén
          <span className="label-badge location">Opcional</span>
        </label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location || ''}
          onChange={onChange}
          placeholder={
            sector.is_panaderia ? 'Ej: Vitrina-A, Horno-2' :
            sector.is_taller ? 'Ej: Estantería-C3, Zona-Motor' :
            'Ej: Pasillo-A-Estante-3'
          }
          className="field-input"
          aria-label="Ubicación física en el almacén"
        />
        <small className="field-help">
          Facilita la localización rápida del producto
        </small>
      </div>

      {/* ============================================ */}
      {/* NOTAS / OBSERVACIONES */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="notes" className="field-label">
          Notas / Observaciones
        </label>
        <textarea
          id="notes"
          name="notes"
          value={formData.notes || ''}
          onChange={onChange}
          placeholder={
            moveType === 'adjustment'
              ? 'Razón del ajuste: merma, rotura, corrección...'
              : 'Observaciones adicionales sobre este movimiento'
          }
          rows={3}
          className="field-textarea"
          aria-label="Notas adicionales del movimiento"
        />
        {moveType === 'adjustment' && (
          <small className="field-help warning">
            ⚠️ Los ajustes de inventario requieren justificación
          </small>
        )}
      </div>

      {/* ============================================ */}
      {/* CAMPOS ESPECÍFICOS POR TIPO DE MOVIMIENTO */}
      {/* ============================================ */}

      {moveType === 'transfer' && (
        <div className="inventory-field">
          <label htmlFor="destination_warehouse" className="field-label">
            Almacén de Destino *
          </label>
          <select
            id="destination_warehouse"
            name="destination_warehouse"
            value={formData.destination_warehouse || ''}
            onChange={onChange}
            required
            className="field-input"
            aria-label="Seleccionar almacén de destino"
          >
            <option value="">-- Seleccionar almacén --</option>
            <option value="main">Almacén Principal</option>
            <option value="retail">Tienda/Punto de Venta</option>
            {sector.is_panaderia && <option value="production">Zona de Producción</option>}
            {sector.is_taller && <option value="workshop">Taller/Zona de Trabajo</option>}
          </select>
        </div>
      )}

      {/* ============================================ */}
      {/* CAMPOS ESPECÍFICOS PANADERÍA */}
      {/* ============================================ */}

      {sector.is_panaderia && moveType === 'in' && (
        <>
          <div className="inventory-field">
            <label htmlFor="production_date" className="field-label">
              🥐 Fecha de Producción
            </label>
            <input
              type="date"
              id="production_date"
              name="production_date"
              value={formData.production_date || new Date().toISOString().split('T')[0]}
              onChange={onChange}
              max={new Date().toISOString().split('T')[0]}
              className="field-input"
              aria-label="Fecha de producción de la hornada"
            />
            <small className="field-help">
              Fecha en que se horneó el producto
            </small>
          </div>

          <div className="inventory-field">
            <label htmlFor="batch_size" className="field-label">
              🥐 Tamaño de Hornada
            </label>
            <input
              type="number"
              id="batch_size"
              name="batch_size"
              value={formData.batch_size || ''}
              onChange={onChange}
              placeholder="Cantidad producida"
              min="1"
              step="1"
              className="field-input"
              aria-label="Tamaño de la hornada producida"
            />
            <small className="field-help">
              Cantidad total producida en esta hornada
            </small>
          </div>
        </>
      )}

      {/* ============================================ */}
      {/* CAMPOS ESPECÍFICOS TALLER */}
      {/* ============================================ */}

      {sector.is_taller && (
        <div className="inventory-field">
          <label htmlFor="supplier_reference" className="field-label">
            🔧 Referencia del Proveedor
          </label>
          <input
            type="text"
            id="supplier_reference"
            name="supplier_reference"
            value={formData.supplier_reference || ''}
            onChange={onChange}
            placeholder="Albarán, factura, orden de compra..."
            className="field-input"
            aria-label="Referencia del documento del proveedor"
          />
          <small className="field-help">
            Número de albarán o factura del proveedor
          </small>
        </div>
      )}

      <style>{`
        .inventory-field {
          margin-bottom: 18px;
        }

        .field-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 6px;
        }

        .label-badge {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          padding: 2px 6px;
          border-radius: 4px;
          letter-spacing: 0.3px;
        }

        .label-badge.expiry {
          background: #fef3c7;
          color: #92400e;
        }

        .label-badge.serial {
          background: #dbeafe;
          color: #1e40af;
        }

        .label-badge.location {
          background: #e5e7eb;
          color: #374151;
        }

        .field-input,
        .field-textarea {
          width: 100%;
          padding: 9px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          font-family: inherit;
          transition: all 0.15s ease;
        }

        .field-input:focus,
        .field-textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .field-textarea {
          resize: vertical;
          line-height: 1.5;
        }

        .field-help {
          display: block;
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
          line-height: 1.4;
        }

        .field-help.warning {
          color: #d97706;
          font-weight: 500;
        }

        /* Responsive */
        @media (max-width: 640px) {
          .field-label {
            font-size: 12px;
            flex-wrap: wrap;
          }

          .label-badge {
            font-size: 9px;
            padding: 1px 4px;
          }

          .field-input,
          .field-textarea {
            font-size: 13px;
          }
        }
      `}</style>
    </>
  )
}

export default ConditionalInventoryFields
