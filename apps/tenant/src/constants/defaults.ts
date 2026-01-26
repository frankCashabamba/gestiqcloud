/**
 * Centralized default values for forms and UI components
 * Helps avoid hardcoded defaults scattered throughout the codebase
 * Changes to defaults should be made in one place
 */

// ============================================================================
// POS & NUMBERING DEFAULTS
// ============================================================================

export const POS_DEFAULTS = {
    // Opening/Closing float amounts
    OPENING_FLOAT: '100.00',

    // Register defaults
    REGISTER_NAME: 'Caja Principal',
    REGISTER_CODE: 'CAJA-1',

    // Tax defaults
    DEFAULT_TAX_RATE: 0,

    // Receipt defaults
    RECEIPT_WIDTH_MM: 80,

    // Return window in days
    RETURN_WINDOW_DAYS: 30,
}

export const NUMBERING_DEFAULTS = {
    // Document series defaults
    DOC_SERIES_FORM: {
        id: '',
        register_id: '',
        doc_type: 'R',
        name: 'R001',
        current_no: 0,
        reset_policy: 'yearly' as 'yearly' | 'never',
        active: true,
    },

    // Counter defaults
    COUNTER_FORM: {
        doc_type: 'pos_receipt',
        year: new Date().getFullYear(),
        series: 'A',
        current_no: 0,
    },
}

// ============================================================================
// PURCHASING & INVENTORY DEFAULTS
// ============================================================================

export const PURCHASING_DEFAULTS = {
    // Tax rate on purchase forms
    TAX_RATE: 0,

    // Default warehouse for imports
    TARGET_WAREHOUSE: 'ALM-1',
}

export const INVENTORY_DEFAULTS = {
    // Currency symbol display
    CURRENCY_SYMBOL: '$',

    // Pagination
    PER_PAGE: 25,

    // Reorder point
    REORDER_POINT_DEFAULT: null,
}

// ============================================================================
// PAGINATION & LIST DEFAULTS
// ============================================================================

export const PAGINATION_DEFAULTS = {
    // Standard pagination sizes across lists
    PER_PAGE_SMALL: 10,
    PER_PAGE_MEDIUM: 25,
    PER_PAGE_LARGE: 50,

    // Default for different modules
    VENTAS_PER_PAGE: 25,
    FINANZAS_PER_PAGE: 25,
    RRHH_PER_PAGE: 25,
    IMPORTACIONES_PER_PAGE: 25,
}

// ============================================================================
// FILTER & SELECTION DEFAULTS
// ============================================================================

export const FILTER_DEFAULTS = {
    // Default filter value for "all items"
    FILTER_ALL: 'all',

    // Default sort order
    SORT_ASC: 'asc',
    SORT_DESC: 'desc',
}

// ============================================================================
// JSON & CONFIGURATION DEFAULTS
// ============================================================================

export const CONFIG_DEFAULTS = {
    // Empty JSON object for settings forms
    EMPTY_JSON: '{}',

    // Invoice configuration defaults
    INVOICE_CONFIG: {},

    // E-invoicing configuration defaults
    EINVOICE_CONFIG: {},

    // Module configurations
    PURCHASES_CONFIG: {},
    EXPENSES_CONFIG: {},
    FINANCE_CONFIG: {},
    HR_CONFIG: {},
    SALES_CONFIG: {},
}

// ============================================================================
// SETTINGS & LOCALIZATION DEFAULTS
// ============================================================================

export const SETTINGS_DEFAULTS = {
    // Locale/Language
    LOCALE: 'es',

    // Timezone
    TIMEZONE: 'America/Guayaquil',

    // Currency code
    CURRENCY: 'USD',

    // Inventory tracking
    TRACK_LOTS: false,
    TRACK_EXPIRY: false,
    ALLOW_NEGATIVE_STOCK: false,

    // Store credit
    STORE_CREDIT_ENABLED: false,
    STORE_CREDIT_SINGLE_USE: false,
    STORE_CREDIT_EXPIRY_MONTHS: null,

    // Price configuration
    PRICE_INCLUDES_TAX: false,
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get a deep copy of defaults to avoid mutation
 * Usage: const form = getFormDefaults('DOC_SERIES')
 */
export function getFormDefaults(formType: keyof typeof NUMBERING_DEFAULTS): any {
    return JSON.parse(JSON.stringify(NUMBERING_DEFAULTS[formType]))
}

/**
 * Reset form to defaults
 * Usage: setForm(getFormDefaults('DOC_SERIES_FORM'))
 */
export function resetToDefaults(formType: string): any {
    const defaultValue = {
        DOC_SERIES: NUMBERING_DEFAULTS.DOC_SERIES_FORM,
        COUNTER: NUMBERING_DEFAULTS.COUNTER_FORM,
    }[formType]

    if (!defaultValue) {
        console.warn(`No defaults found for form type: ${formType}`)
        return {}
    }

    return JSON.parse(JSON.stringify(defaultValue))
}
