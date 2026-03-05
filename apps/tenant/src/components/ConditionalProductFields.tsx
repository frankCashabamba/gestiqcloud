/**
 * ConditionalProductFields
 *
 * Product fields that appear/disappear based on sector configuration
 *
 * PHASE 4 STEP 4: Dynamic placeholders from DB
 * - Replaces hardcoded placeholders with values from template_config
 * - Uses useSectorPlaceholders to load dynamically
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import { useCompanyFeatures, useCompanySector } from '../contexts/CompanyConfigContext'
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
  const { t } = useTranslation('common')
  const features = useCompanyFeatures()
  const sector = useCompanySector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'products')

  return (
    <>
      {/* ============================================ */}
      {/* CONDITIONAL INVENTORY FIELDS */}
      {/* ============================================ */}

      {/* Expiration Date (bakery, food only) */}
      {features.inventory_expiry_tracking && (
        <div className="form-field">
          <label htmlFor="expires_at" className="form-label">
            {t('productFields.expirationDate')} {features.inventory_expiry_tracking && '*'}
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
              {t('productFields.perishableHelp')}
            </small>
          )}
        </div>
      )}

      {/* Lot/Batch (bakery, workshop) */}
      {features.inventory_lot_tracking && (
        <div className="form-field">
          <label htmlFor="lot" className="form-label">
            {t('productFields.lotNumber')}
          </label>
          <input
            type="text"
            id="lot"
            name="lot"
            value={formData.lot || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'lote', t('productFields.lotNumberPlaceholder'))}
            className="form-input"
          />
          <small className="form-help">
            {t('productFields.lotHelp')}
          </small>
        </div>
      )}

      {/* Serial Number (workshop, electronics retail) */}
      {features.inventory_serial_tracking && (
        <div className="form-field">
          <label htmlFor="serial_number" className="form-label">
            {t('productFields.serialNumber')}
          </label>
          <input
            type="text"
            id="serial_number"
            name="serial_number"
            value={formData.serial_number || ''}
            onChange={onChange}
            placeholder={getFieldPlaceholder(placeholders, 'numero_serie', t('productFields.serialNumberPlaceholder'))}
            className="form-input"
          />
          <small className="form-help">
            {t('productFields.serialHelp')}
          </small>
        </div>
      )}

      {/* ============================================ */}
      {/* CONDITIONAL POS FIELDS */}
      {/* ============================================ */}

      {/* Sell by Weight (bakery) */}
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
              <span>{t('productFields.soldByWeight')}</span>
            </label>
          </div>

          {formData.sold_by_weight && (
            <div className="form-field">
              <label htmlFor="weight_unit" className="form-label">
                {t('productFields.weightUnit')} *
              </label>
              <select
                id="weight_unit"
                name="weight_unit"
                value={formData.weight_unit || 'kg'}
                onChange={onChange}
                required
                className="form-input"
              >
                <option value="kg">{t('productFields.kilograms')}</option>
                <option value="g">{t('productFields.grams')}</option>
                <option value="lb">{t('productFields.pounds')}</option>
              </select>
            </div>
          )}
        </>
      )}

      {/* ============================================ */}
      {/* SECTOR-SPECIFIC FIELDS */}
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
