"""Aggregation layer for imports services package.

Nota: coexistimos con `services.py` en el mismo directorio. Para exponer
`procesar_documento` y helpers definidos allí, cargamos ese módulo como
implementación `_services_impl` y re-exportamos lo necesario.
"""

from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

from app.modules.imports.services.classifier import FileClassifier, classifier
from app.modules.imports.services.decision_logger import (
    DecisionEntry,
    DecisionLog,
    DecisionLogger,
    DecisionStep,
    StepTimer,
    decision_logger,
)
from app.modules.imports.services.ocr_service import (
    DocumentLayout,
    OCRResult,
    OCRService,
    ocr_service,
)

_impl_path = Path(__file__).resolve().parent.parent / "services.py"
_spec = spec_from_loader(
    "_imports_services_impl", SourceFileLoader("_imports_services_impl", str(_impl_path))
)
_services_impl = module_from_spec(_spec) if _spec else None
if _spec and _spec.loader and _services_impl:
    _spec.loader.exec_module(_services_impl)
    procesar_documento = getattr(_services_impl, "procesar_documento", None)
    limpiar_texto_ocr = getattr(_services_impl, "limpiar_texto_ocr", None)
    extraer_texto_ocr_hibrido_paginas = getattr(
        _services_impl, "extraer_texto_ocr_hibrido_paginas", None
    )
else:  # pragma: no cover - fallback if spec fails
    procesar_documento = None
    limpiar_texto_ocr = None
    extraer_texto_ocr_hibrido_paginas = None

__all__ = [
    "FileClassifier",
    "classifier",
    "DecisionEntry",
    "DecisionLog",
    "DecisionLogger",
    "DecisionStep",
    "StepTimer",
    "decision_logger",
    "DocumentLayout",
    "OCRResult",
    "OCRService",
    "ocr_service",
    "procesar_documento",
    "limpiar_texto_ocr",
    "extraer_texto_ocr_hibrido_paginas",
]
