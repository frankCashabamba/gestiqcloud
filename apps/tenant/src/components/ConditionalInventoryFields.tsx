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
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('common')
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
            {t('inventoryFields.expirationDate')} {features.inventory_expiry_tracking && '*'}
            <span className="label-badge expiry">
              {features.inventory_expiry_tracking ? `🥐 ${t('inventoryFields.required')}` : t('inventoryFields.optional')}
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
            aria-label={t('inventoryFields.ariaExpirationDate')}
          />
          {features.inventory_expiry_tracking && (
            <small className="field-help warning">
              ⚠️ {t('inventoryFields.perishableWarning')}
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
            📦 {t('inventoryFields.lotNumber')}
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'lote', t('inventoryFields.lotNumberPlaceholder'))}
            className="field-input"
            aria-label={t('inventoryFields.ariaLotNumber')}
          />
          <small className="field-help">
            {t('inventoryFields.lotHelp')}
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* SERIAL NUMBER (Workshop, Electronics Retail) */}
      {/* ============================================ */}

      {features.inventory_serial_tracking && (
        <div className="inventory-field">
          <label htmlFor="serial_number" className="field-label">
            📱 {t('inventoryFields.serialNumber')}
          </label>
          <input
            type="text"
            id="serial_number"
            name="serial_number"
            value={formData.serial_number || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'numero_serie', t('inventoryFields.serialNumberPlaceholder'))}
            className="field-input"
            aria-label={t('inventoryFields.ariaSerialNumber')}
          />
          <small className="field-help">
            {t('inventoryFields.serialHelp')}
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* WAREHOUSE LOCATION */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="location" className="field-label">
          {t('inventoryFields.warehouseLocation')}
          <span className="label-badge location">{t('inventoryFields.optional')}</span>
        </label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location || ''}
          onChange={onChange}
          placeholder={getFieldPlaceholder(placeholders, 'ubicacion', t('inventoryFields.locationPlaceholder'))}
          className="field-input"
          aria-label={t('inventoryFields.ariaLocation')}
        />
        <small className="field-help">
          {t('inventoryFields.locationHelp')}
        </small>
      </div>

      {/* ============================================ */}
      {/* NOTES / OBSERVATIONS */}
      {/* ============================================ */}

      <div className="inventory-field">
        <label htmlFor="notes" className="field-label">
          {t('inventoryFields.notes')}
        </label>
        <textarea
          id="notes"
          name="notes"
          value={formData.notes || ''}
          onChange={onChange}
          placeholder={
            moveType === 'adjustment'
              ? t('inventoryFields.adjustmentPlaceholder')
              : t('inventoryFields.observationsPlaceholder')
          }
          rows={3}
          className="field-textarea"
          aria-label={t('inventoryFields.ariaMovementNotes')}
        />
        {moveType === 'adjustment' && (
          <small className="field-help warning">
            ⚠️ {t('inventoryFields.adjustmentWarning')}
          </small>
        )}
      </div>

      {/* ============================================ */}
      {/* FIELDS SPECIFIC TO MOVEMENT TYPE */}
      {/* ============================================ */}

      {moveType === 'transfer' && (
        <div className="inventory-field">
          <label htmlFor="destination_warehouse" className="field-label">
            {t('inventoryFields.destinationWarehouse')} *
          </label>
          <select
            id="destination_warehouse"
            name="destination_warehouse"
            value={formData.destination_warehouse || ''}
            onChange={onChange}
            required
            className="field-input"
            aria-label={t('inventoryFields.ariaSelectWarehouse')}
          >
            <option value="">{t('inventoryFields.selectWarehouse')}</option>
            <option value="main">{t('inventoryFields.mainWarehouse')}</option>
            <option value="retail">{t('inventoryFields.storePointOfSale')}</option>
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
          color: var(--gc-foreground);
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
          background: var(--gc-border);
          color: var(--gc-foreground);
        }

        .field-input,
        .field-textarea {
          width: 100%;
          padding: 9px 12px;
          border: 1px solid var(--gc-border);
          border-radius: 6px;
          font-size: 14px;
          font-family: inherit;
          transition: all 0.15s ease;
        }

        .field-input:focus,
        .field-textarea:focus {
          outline: none;
          border-color: var(--gc-primary);
          box-shadow: 0 0 0 3px color-mix(in srgb, var(--gc-primary) 10%, transparent);
        }

        .field-textarea {
          resize: vertical;
          line-height: 1.5;
        }

        .field-help {
          display: block;
          font-size: 12px;
          color: var(--gc-muted);
          margin-top: 4px;
          line-height: 1.4;
        }

        .field-help.warning {
          color: var(--gc-warning);
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
