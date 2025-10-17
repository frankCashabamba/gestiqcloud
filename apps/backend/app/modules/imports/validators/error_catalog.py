from typing import TypedDict, Literal


class ErrorDefinition(TypedDict):
    code: str
    message_template: str
    severity: Literal["error", "warning"]
    suggested_action: str


ERROR_CATALOG: dict[str, ErrorDefinition] = {
    "INVALID_TAX_ID_FORMAT": {
        "code": "INVALID_TAX_ID_FORMAT",
        "message_template": "Formato de identificación fiscal inválido: {value}. Se espera {expected_format}",
        "severity": "error",
        "suggested_action": "Verifica que el RUC/NIF/CIF cumpla con el formato requerido del país",
    },
    "INVALID_TAX_ID_CHECKSUM": {
        "code": "INVALID_TAX_ID_CHECKSUM",
        "message_template": "Dígito verificador incorrecto en identificación fiscal: {value}",
        "severity": "error",
        "suggested_action": "Revisa que el número sea correcto o regenera el dígito de control",
    },
    "INVALID_TAX_RATE": {
        "code": "INVALID_TAX_RATE",
        "message_template": "Tasa de impuesto inválida: {rate}%. Las tasas válidas para {country} son: {valid_rates}",
        "severity": "error",
        "suggested_action": "Ajusta la tasa al valor oficial vigente en el país",
    },
    "TOTALS_MISMATCH": {
        "code": "TOTALS_MISMATCH",
        "message_template": "Los totales no cuadran: base ({net}) + impuesto ({tax}) ≠ total ({total}). Diferencia: {diff}",
        "severity": "error",
        "suggested_action": "Recalcula los importes o revisa los redondeos",
    },
    "INVALID_DATE_FORMAT": {
        "code": "INVALID_DATE_FORMAT",
        "message_template": "Formato de fecha inválido: {value}. Se espera ISO 8601 (YYYY-MM-DD) o DD/MM/YYYY",
        "severity": "error",
        "suggested_action": "Convierte la fecha al formato esperado",
    },
    "MISSING_REQUIRED_FIELD": {
        "code": "MISSING_REQUIRED_FIELD",
        "message_template": "Campo obligatorio faltante: {field}",
        "severity": "error",
        "suggested_action": "Proporciona un valor para el campo requerido",
    },
    "EMPTY_VALUE": {
        "code": "EMPTY_VALUE",
        "message_template": "El campo {field} no puede estar vacío",
        "severity": "error",
        "suggested_action": "Ingresa un valor no vacío",
    },
    "INVALID_INVOICE_NUMBER_FORMAT": {
        "code": "INVALID_INVOICE_NUMBER_FORMAT",
        "message_template": "Formato de número de factura inválido: {value}. Se espera {expected_format}",
        "severity": "error",
        "suggested_action": "Ajusta el número al formato requerido del país",
    },
    "INVALID_CLAVE_ACCESO": {
        "code": "INVALID_CLAVE_ACCESO",
        "message_template": "Clave de acceso SRI inválida: {value}. Debe tener 49 dígitos y checksum válido",
        "severity": "error",
        "suggested_action": "Regenera la clave de acceso con el algoritmo módulo 11",
    },
    "INVALID_CURRENCY": {
        "code": "INVALID_CURRENCY",
        "message_template": "Código de moneda inválido: {value}. Se espera código ISO 4217 (ej: USD, EUR)",
        "severity": "error",
        "suggested_action": "Usa un código de 3 letras según ISO 4217",
    },
    "FUTURE_DATE": {
        "code": "FUTURE_DATE",
        "message_template": "La fecha {field} no puede ser futura: {value}",
        "severity": "warning",
        "suggested_action": "Verifica que la fecha sea correcta",
    },
    "NEGATIVE_AMOUNT": {
        "code": "NEGATIVE_AMOUNT",
        "message_template": "El importe {field} no puede ser negativo: {value}",
        "severity": "error",
        "suggested_action": "Usa valores positivos o crea un documento de ajuste (nota de crédito)",
    },
}


class ValidationError(TypedDict):
    code: str
    field: str
    message: str
    severity: Literal["error", "warning"]
    params: dict
