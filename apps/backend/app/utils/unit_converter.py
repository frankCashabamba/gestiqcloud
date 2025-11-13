"""
Unit Converter - Sistema de conversión de unidades de medida
Soporta peso, volumen y temperatura para recetas profesionales
"""

from decimal import Decimal
from typing import Dict, Optional
from enum import Enum


class UnitType(str, Enum):
    WEIGHT = "weight"
    VOLUME = "volume"
    TEMPERATURE = "temperature"
    COUNT = "count"


# ============================================================================
# TABLAS DE CONVERSIÓN (a unidades base)
# ============================================================================

# Peso: Base = kilogramo (kg)
WEIGHT_TO_KG: Dict[str, Decimal] = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
    "lb": Decimal("0.453592"),  # 1 lb = 0.453592 kg
    "oz": Decimal("0.0283495"),  # 1 oz = 0.0283495 kg
    "ton": Decimal("1000"),
    "mg": Decimal("0.000001"),
}

# Volumen: Base = litro (L)
VOLUME_TO_L: Dict[str, Decimal] = {
    "L": Decimal("1"),
    "ml": Decimal("0.001"),
    "gal": Decimal("3.78541"),  # 1 galón US = 3.78541 L
    "qt": Decimal("0.946353"),  # 1 cuarto US = 0.946353 L
    "pt": Decimal("0.473176"),  # 1 pinta US
    "cup": Decimal("0.236588"),  # 1 taza US
    "fl_oz": Decimal("0.0295735"),  # 1 onza fluida US
    "tbsp": Decimal("0.0147868"),  # 1 cucharada
    "tsp": Decimal("0.00492892"),  # 1 cucharadita
}

# Temperatura: Base = Celsius (C)
# No se usa tabla, sino funciones de conversión


# ============================================================================
# FUNCIONES DE CONVERSIÓN
# ============================================================================


def get_unit_type(unit: str) -> Optional[UnitType]:
    """Determina el tipo de unidad"""
    unit_lower = unit.lower()

    if unit_lower in [k.lower() for k in WEIGHT_TO_KG.keys()]:
        return UnitType.WEIGHT
    elif unit_lower in [k.lower() for k in VOLUME_TO_L.keys()]:
        return UnitType.VOLUME
    elif unit_lower in ["c", "f", "k", "celsius", "fahrenheit", "kelvin"]:
        return UnitType.TEMPERATURE
    elif unit_lower in ["uds", "unidades", "pcs", "piezas", "units"]:
        return UnitType.COUNT

    return None


def normalize_unit_name(unit: str) -> str:
    """Normaliza nombres de unidades a formato estándar"""
    unit_map = {
        # Peso
        "kilogramo": "kg",
        "kilogramos": "kg",
        "gramo": "g",
        "gramos": "g",
        "libra": "lb",
        "libras": "lb",
        "onza": "oz",
        "onzas": "oz",
        "tonelada": "ton",
        # Volumen
        "litro": "L",
        "litros": "L",
        "mililitro": "ml",
        "mililitros": "ml",
        "galon": "gal",
        "galones": "gal",
        # Conteo
        "unidad": "uds",
        "unidades": "uds",
        "pieza": "uds",
        "piezas": "uds",
        # Temperatura
        "celsius": "C",
        "fahrenheit": "F",
        "kelvin": "K",
    }

    return unit_map.get(unit.lower(), unit)


def convert_weight(qty: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Convierte entre unidades de peso"""
    from_unit = normalize_unit_name(from_unit)
    to_unit = normalize_unit_name(to_unit)

    if from_unit not in WEIGHT_TO_KG:
        raise ValueError(f"Unidad de peso desconocida: {from_unit}")
    if to_unit not in WEIGHT_TO_KG:
        raise ValueError(f"Unidad de peso desconocida: {to_unit}")

    # Convertir a kg (base), luego a unidad destino
    kg_value = qty * WEIGHT_TO_KG[from_unit]
    result = kg_value / WEIGHT_TO_KG[to_unit]

    return result


def convert_volume(qty: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Convierte entre unidades de volumen"""
    from_unit = normalize_unit_name(from_unit)
    to_unit = normalize_unit_name(to_unit)

    if from_unit not in VOLUME_TO_L:
        raise ValueError(f"Unidad de volumen desconocida: {from_unit}")
    if to_unit not in VOLUME_TO_L:
        raise ValueError(f"Unidad de volumen desconocida: {to_unit}")

    # Convertir a L (base), luego a unidad destino
    l_value = qty * VOLUME_TO_L[from_unit]
    result = l_value / VOLUME_TO_L[to_unit]

    return result


def convert_temperature(temp: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Convierte entre unidades de temperatura"""
    from_unit = normalize_unit_name(from_unit).upper()
    to_unit = normalize_unit_name(to_unit).upper()

    # Convertir a Celsius (base)
    if from_unit == "C":
        celsius = temp
    elif from_unit == "F":
        celsius = (temp - 32) * Decimal("5") / Decimal("9")
    elif from_unit == "K":
        celsius = temp - Decimal("273.15")
    else:
        raise ValueError(f"Unidad de temperatura desconocida: {from_unit}")

    # Convertir a unidad destino
    if to_unit == "C":
        return celsius
    elif to_unit == "F":
        return celsius * Decimal("9") / Decimal("5") + 32
    elif to_unit == "K":
        return celsius + Decimal("273.15")
    else:
        raise ValueError(f"Unidad de temperatura desconocida: {to_unit}")


def convert(qty: float, from_unit: str, to_unit: str) -> float:
    """
    Convierte cantidad de una unidad a otra

    Args:
        qty: Cantidad a convertir
        from_unit: Unidad origen
        to_unit: Unidad destino

    Returns:
        Cantidad convertida

    Raises:
        ValueError: Si las unidades son incompatibles o desconocidas
    """
    qty_decimal = Decimal(str(qty))

    from_type = get_unit_type(from_unit)
    to_type = get_unit_type(to_unit)

    if from_type is None:
        raise ValueError(f"Unidad desconocida: {from_unit}")
    if to_type is None:
        raise ValueError(f"Unidad desconocida: {to_unit}")
    if from_type != to_type:
        raise ValueError(f"No se puede convertir {from_type.value} a {to_type.value}")

    # Unidades iguales, no convertir
    if normalize_unit_name(from_unit) == normalize_unit_name(to_unit):
        return float(qty)

    # Convertir según tipo
    if from_type == UnitType.WEIGHT:
        result = convert_weight(qty_decimal, from_unit, to_unit)
    elif from_type == UnitType.VOLUME:
        result = convert_volume(qty_decimal, from_unit, to_unit)
    elif from_type == UnitType.TEMPERATURE:
        result = convert_temperature(qty_decimal, from_unit, to_unit)
    elif from_type == UnitType.COUNT:
        # Conteo no requiere conversión
        result = qty_decimal
    else:
        raise ValueError(f"Tipo de unidad no soportado: {from_type}")

    return float(result)


def normalize_to_base(qty: float, unit: str) -> tuple[float, str]:
    """
    Normaliza cantidad a unidad base del sistema

    Args:
        qty: Cantidad
        unit: Unidad

    Returns:
        Tupla (cantidad_normalizada, unidad_base)

    Ejemplos:
        normalize_to_base(50, "lb") -> (22.6796, "kg")
        normalize_to_base(1, "gal") -> (3.78541, "L")
    """
    unit_type = get_unit_type(unit)

    if unit_type == UnitType.WEIGHT:
        return convert(qty, unit, "kg"), "kg"
    elif unit_type == UnitType.VOLUME:
        return convert(qty, unit, "L"), "L"
    elif unit_type == UnitType.TEMPERATURE:
        return convert(qty, unit, "C"), "C"
    elif unit_type == UnitType.COUNT:
        return qty, "uds"
    else:
        raise ValueError(f"Unidad desconocida: {unit}")


def format_qty(qty: float, unit: str, decimals: int = 2) -> str:
    """
    Formatea cantidad con unidad para presentación

    Args:
        qty: Cantidad
        unit: Unidad
        decimals: Decimales a mostrar

    Returns:
        String formateado: "50.00 lb", "3.79 L"
    """
    return f"{qty:.{decimals}f} {unit}"


# ============================================================================
# VALIDACIONES
# ============================================================================


def is_valid_unit(unit: str) -> bool:
    """Verifica si una unidad es válida"""
    return get_unit_type(unit) is not None


def are_compatible_units(unit1: str, unit2: str) -> bool:
    """Verifica si dos unidades son compatibles (mismo tipo)"""
    type1 = get_unit_type(unit1)
    type2 = get_unit_type(unit2)

    if type1 is None or type2 is None:
        return False

    return type1 == type2


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

if __name__ == "__main__":
    # Peso
    print(convert(50, "lb", "kg"))  # 22.6796 kg
    print(convert(1, "kg", "lb"))  # 2.20462 lb
    print(convert(16, "oz", "lb"))  # 1.0 lb

    # Volumen
    print(convert(1, "gal", "L"))  # 3.78541 L
    print(convert(1, "L", "ml"))  # 1000 ml

    # Temperatura
    print(convert(32, "F", "C"))  # 0 C
    print(convert(100, "C", "F"))  # 212 F

    # Normalización
    print(normalize_to_base(50, "lb"))  # (22.6796, "kg")
    print(normalize_to_base(2, "gal"))  # (7.57082, "L")

    # Formato
    print(format_qty(22.6796, "kg", 2))  # "22.68 kg"
