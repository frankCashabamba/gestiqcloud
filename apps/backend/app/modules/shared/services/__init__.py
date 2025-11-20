"""
Servicios compartidos entre módulos.
"""

from .document_converter import DocumentConverter
from .numbering import generar_numero_documento, validar_numero_unico

__all__ = [
    "generar_numero_documento",
    "validar_numero_unico",
    "DocumentConverter",
]
