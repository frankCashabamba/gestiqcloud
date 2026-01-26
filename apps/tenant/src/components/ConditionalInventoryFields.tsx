/**
 * ConditionalInventoryFields
 *
 * Inventory movement fields that appear based on sector configuration
 * Similar to ConditionalProductFields but for stock movements
 *
 * PHASE 4 STEP 4: Dynamic placeholders from DB
 * - Replaces hardcoded placeholders with values from template_config
 * - Uses useSectorPlaceholders to load dynamically
 */
import React from 'react'
import { useCompanyFeatures, useCompanySector } from '../contexts/CompanyConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../hooks/useSectorPlaceholders'

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
  const features = useCompanyFeatures()
  const sector = useCompanySector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'inventory')

  const isIncoming = moveType === 'in' || moveType === 'adjustment'

  return (
    <>
      {/* ============================================ */}
      {/* EXPIRATION DATE (Bakery, Food) */}
      {/* ============================================ */}

      {features.inventory_expiry_tracking && isIncoming && (
        <div className="inventory-field">
          <label htmlFor="expires_at" className="field-label">
            Expiration Date {features.inventory_expiry_tracking && '*'}
            <span className="label-badge expiry">
              {features.inventory_expiry_tracking ? '🥐 Required' : 'Optional'}
            </span>
          </label>
          <input
            type="date"
            id="expires_at"
            name="expires_at"
            value={formData.expires_at || ''}
            onChange={onChange}
            min={new Date().toISOString().split('T')[0]}
            required={features.inventory_expiry_tracking}
            className="field-input"
            aria-label="Product expiration date"
          />
          {features.inventory_expiry_tracking && (
            <small className="field-help warning">
              ⚠️ Perishable products require a mandatory expiration date
            </small>
          )}
        </div>
      )}

      {/* ============================================ */}
      {/* LOT / BATCH */}
      {/* ============================================ */}

      {features.inventory_lot_tracking && isIncoming && (
        <div className="inventory-field">
          <label htmlFor="lot" className="field-label">
            📦 Lot Number
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'lote', 'Lot number')}
            className="field-input"
            aria-label="Lot or batch number"
          />
          <small className="field-help">
            Identifies the production lot for traceability
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* SERIAL NUMBER (Workshop, Electronics Retail) */}
      {/* ============================================ */}

      {features.inventory_serial_tracking && (
        <div className="inventory-field">
          <label htmlFor="serial_number" className="field-label">
            📱 Serial Number
          </label>
          <input
            type="text"
            id="serial_number"
            name="serial_number"
            value={formData.serial_number || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'numero_serie', 'E.g.: SN-123456789')}
            className="field-input"
            aria-label="Serial number for individual tracking"
          />
          <small className="field-help">
            For individual product tracking
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* WAREHOUSE LOCATION */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="location" className="field-label">
          Warehouse Location
          <span className="label-badge location">Optional</span>
        </label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location || ''}
          onChange={onChange}
          placeholder={getFieldPlaceholder(placeholders, 'ubicacion', 'E.g.: Aisle-A-Shelf-3')}
          className="field-input"
          aria-label="Physical location in the warehouse"
        />
        <small className="field-help">
          Facilitates quick product location
        </small>
      </div>

      {/* ============================================ */}
      {/* NOTES / OBSERVATIONS */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="notes" className="field-label">
          Notes / Observations
        </label>
        <textarea
          id="notes"
          name="notes"
          value={formData.notes || ''}
          onChange={onChange}
          placeholder={
            moveType === 'adjustment'
              ? 'Reason for adjustment: shrinkage, breakage, correction...'
              : 'Additional observations about this movement'
          }
          rows={3}
          className="field-textarea"
          aria-label="Additional movement notes"
        />
        {moveType === 'adjustment' && (
          <small className="field-help warning">
            ⚠️ Inventory adjustments require justification
          </small>
        )}
      </div>

      {/* ============================================ */}
      {/* FIELDS SPECIFIC TO MOVEMENT TYPE */}
      {/* ============================================ */}

      {moveType === 'transfer' && (
        <div className="inventory-field">
          <label htmlFor="destination_warehouse" className="field-label">
            Destination Warehouse *
          </label>
          <select
            id="destination_warehouse"
            name="destination_warehouse"
            value={formData.destination_warehouse || ''}
            onChange={onChange}
            required
            className="field-input"
            aria-label="Select destination warehouse"
          >
            <option value="">-- Select warehouse --</option>
            <option value="main">Main Warehouse</option>
            <option value="retail">Store/Point of Sale</option>
          </select>
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
