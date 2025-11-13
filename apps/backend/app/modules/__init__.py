"""Package root for vertical-slice modules (DDD style).

Provides lazy attribute access to subpackages so that dotted patch targets like
`app.modules.einvoicing.application.use_cases` resolve even if importlib falls
back to getattr traversal.
"""

import importlib
from typing import Any


def __getattr__(name: str) -> Any:  # PEP 562 lazy import
    if name == "einvoicing":
        return importlib.import_module(__name__ + ".einvoicing")
    raise AttributeError(name)
