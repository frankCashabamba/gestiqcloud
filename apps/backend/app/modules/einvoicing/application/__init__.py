"""E-invoicing application subpackage initializer.

Expose `use_cases` lazily via module-level __getattr__ so that unittest.mock
patch targets resolve without importing heavy dependencies prematurely.
"""

from typing import Any
import importlib


def __getattr__(name: str) -> Any:  # PEP 562 lazy attribute loader
    if name == "use_cases":
        return importlib.import_module(__name__ + ".use_cases")
    raise AttributeError(name)
