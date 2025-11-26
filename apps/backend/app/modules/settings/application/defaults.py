"""Default Settings per Module and Country"""

from typing import Any

# Default settings for Spain
DEFAULT_SETTINGS_ES: dict[str, Any] = {
    "global": {
        "locale": "es_ES",
        "timezone": "Europe/Madrid",
        "currency": "EUR",
        "country": "ES",
        "date_format": "dd/MM/yyyy",
        "number_format": "es-ES",
        "decimal_separator": ",",
        "thousands_separator": ".",
    },
    "pos": {
        "enabled": True,
        "receipt_width_mm": 58,
        "print_mode": "system",  # 'system', 'escpos', 'pdf'
        "tax_included": True,
        "default_tax_rate": 0.21,  # IVA 21%
        "show_tax_breakdown": True,
        "allow_negative_stock": False,
        "require_customer_for_invoice": True,
        "return_window_days": 15,
        "store_credit": {
            "enabled": True,
            "single_use": True,
            "expiry_months": 12,
            "min_amount": 5.00,
        },
        "payment_methods": ["cash", "card", "store_credit", "link"],
        "auto_print_receipt": True,
        "barcode_scanner": {
            "enabled": True,
            "mode": "camera",  # 'camera', 'usb', 'bluetooth'
        },
        "cash_drawer": {"enabled": False, "kick_code": "ESC p 0 25 250"},
    },
    "inventory": {
        "enabled": True,
        "track_lots": True,
        "track_expiry": True,
        "track_serial": False,
        "multiple_warehouses": False,
        "allow_negative": False,
        "reorder_point_enabled": True,
        "auto_reserve_on_sale": True,
        "valuation_method": "fifo",  # 'fifo', 'lifo', 'average'
        "count_frequency_days": 90,
    },
    "invoicing": {
        "enabled": True,
        "auto_numbering": True,
        "series_format": "{year}-{series}-{number:05d}",
        "default_series": "F",
        "payment_terms_days": 30,
        "show_discount": True,
        "show_unit_price": True,
        "show_tax_per_line": True,
        "require_customer": True,
        "allow_future_date": False,
        "credit_note_auto_series": "NC",
    },
    "einvoicing": {
        "enabled": True,
        "provider": "facturae",  # ES: facturae
        "auto_send": False,
        "format": "facturae_3.2.2",
        "signature_required": True,
        "batch_mode": False,
        "sii_enabled": False,  # SII para grandes empresas
        "sii_auto_submit": False,
    },
    "purchases": {
        "enabled": True,
        "auto_numbering": True,
        "default_series": "PC",
        "approve_required": True,
        "match_po_to_receipt": True,
        "allow_over_receipt": False,
        "three_way_match": False,  # PO + Receipt + Invoice
    },
    "expenses": {
        "enabled": True,
        "require_approval": True,
        "categories": ["travel", "supplies", "utilities", "marketing", "other"],
        "receipt_required": True,
        "mileage_rate": 0.19,  # EUR/km
        "per_diem_enabled": False,
    },
    "finance": {
        "enabled": True,
        "chart_of_accounts": "pyme_es",
        "fiscal_year_start": "01-01",
        "vat_rates": [
            {"name": "Superreducido", "rate": 0.04},
            {"name": "Reducido", "rate": 0.10},
            {"name": "General", "rate": 0.21},
            {"name": "Exento", "rate": 0.00},
        ],
        "retention_irpf_default": 0.15,
        "auto_reconcile": False,
        "bank_sync_enabled": False,
    },
    "hr": {
        "enabled": False,
        "payroll_enabled": False,
        "attendance_tracking": False,
        "leave_management": False,
        "contract_templates": [],
    },
    "sales": {
        "enabled": True,
        "quotes_enabled": True,
        "quote_validity_days": 30,
        "auto_convert_quote_to_order": False,
        "delivery_notes_enabled": True,
        "backorders_allowed": True,
        "discount_max_percent": 50.0,
    },
    "crm": {
        "enabled": True,
        "lead_stages": ["new", "contacted", "qualified", "proposal", "won", "lost"],
        "auto_assign_leads": False,
        "email_integration": False,
        "calendar_sync": False,
    },
    "imports": {
        "enabled": True,
        "auto_validate": True,
        "validate_currency": True,
        "require_categories": True,
        "batch_size": 100,
        "allow_duplicates": False,
    },
    "reports": {
        "enabled": True,
        "export_formats": ["pdf", "xlsx", "csv"],
        "auto_schedule": False,
        "retention_days": 365,
    },
}

# Default settings for Ecuador
DEFAULT_SETTINGS_EC: dict[str, Any] = {
    "global": {
        "locale": "es_EC",
        "timezone": "America/Guayaquil",
        "currency": "USD",
        "country": "EC",
        "date_format": "dd/MM/yyyy",
        "number_format": "es-EC",
        "decimal_separator": ".",
        "thousands_separator": ",",
    },
    "pos": {
        "enabled": True,
        "receipt_width_mm": 80,
        "print_mode": "system",
        "tax_included": True,
        "default_tax_rate": 0.15,  # IVA 15% Ecuador
        "show_tax_breakdown": True,
        "allow_negative_stock": False,
        "require_customer_for_invoice": True,
        "return_window_days": 15,
        "store_credit": {
            "enabled": True,
            "single_use": False,  # Ecuador permite uso múltiple
            "expiry_months": 24,
            "min_amount": 5.00,
        },
        "payment_methods": ["cash", "card", "store_credit", "link"],
        "auto_print_receipt": True,
        "barcode_scanner": {"enabled": True, "mode": "camera"},
        "cash_drawer": {"enabled": False, "kick_code": "ESC p 0 25 250"},
    },
    "inventory": {
        "enabled": True,
        "track_lots": True,
        "track_expiry": True,
        "track_serial": False,
        "multiple_warehouses": False,
        "allow_negative": False,
        "reorder_point_enabled": True,
        "auto_reserve_on_sale": True,
        "valuation_method": "average",
        "count_frequency_days": 90,
    },
    "invoicing": {
        "enabled": True,
        "auto_numbering": True,
        "series_format": "{establishment}-{point}-{number:09d}",  # EC: 001-001-000000001
        "default_series": "001-001",
        "payment_terms_days": 30,
        "show_discount": True,
        "show_unit_price": True,
        "show_tax_per_line": True,
        "require_customer": True,
        "allow_future_date": False,
        "credit_note_auto_series": "001-002",
    },
    "einvoicing": {
        "enabled": True,
        "provider": "sri",  # EC: SRI
        "auto_send": False,
        "format": "sri_xml_1.0",
        "signature_required": True,
        "batch_mode": False,
        "test_mode": False,
        "ambiente": "1",  # 1=pruebas, 2=producción
    },
    "purchases": {
        "enabled": True,
        "auto_numbering": True,
        "default_series": "OC",
        "approve_required": True,
        "match_po_to_receipt": True,
        "allow_over_receipt": False,
        "three_way_match": False,
    },
    "expenses": {
        "enabled": True,
        "require_approval": True,
        "categories": ["travel", "supplies", "utilities", "marketing", "other"],
        "receipt_required": True,
        "mileage_rate": 0.30,  # USD/km Ecuador
        "per_diem_enabled": False,
    },
    "finance": {
        "enabled": True,
        "chart_of_accounts": "niif_ec",
        "fiscal_year_start": "01-01",
        "vat_rates": [
            {"name": "IVA 15%", "rate": 0.15},
            {"name": "IVA 0%", "rate": 0.00},
        ],
        "retention_enabled": True,
        "retention_ir_rates": [0.01, 0.02, 0.08, 0.10],
        "retention_iva_rates": [0.30, 0.70, 1.00],
        "auto_reconcile": False,
        "bank_sync_enabled": False,
    },
    "hr": {
        "enabled": False,
        "payroll_enabled": False,
        "attendance_tracking": False,
        "leave_management": False,
        "contract_templates": [],
    },
    "sales": {
        "enabled": True,
        "quotes_enabled": True,
        "quote_validity_days": 30,
        "auto_convert_quote_to_order": False,
        "delivery_notes_enabled": True,
        "backorders_allowed": True,
        "discount_max_percent": 50.0,
    },
    "crm": {
        "enabled": True,
        "lead_stages": ["new", "contacted", "qualified", "proposal", "won", "lost"],
        "auto_assign_leads": False,
        "email_integration": False,
        "calendar_sync": False,
    },
    "imports": {
        "enabled": True,
        "auto_validate": True,
        "validate_currency": True,
        "require_categories": True,
        "batch_size": 100,
        "allow_duplicates": False,
    },
    "reports": {
        "enabled": True,
        "export_formats": ["pdf", "xlsx", "csv"],
        "auto_schedule": False,
        "retention_days": 365,
    },
}

# Default settings (Spain as base)
DEFAULT_SETTINGS = DEFAULT_SETTINGS_ES


def get_default_settings(country: str = "ES") -> dict[str, Any]:
    """Get default settings by country"""
    if country.upper() == "EC":
        return DEFAULT_SETTINGS_EC.copy()
    return DEFAULT_SETTINGS_ES.copy()
