from __future__ import annotations

import pkgutil
from importlib import import_module
from typing import Iterable, List

from .models import ModuleManifest


def _iter_subpackages(pkg_name: str) -> Iterable[str]:
    """Yield dotted module names for subpackages of `pkg_name`."""
    pkg = import_module(pkg_name)
    if not hasattr(pkg, "__path__"):
        return []  # type: ignore[return-value]
    for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        yield m.name


def discover_manifests() -> List[ModuleManifest]:
    """Discover MANIFEST objects defined in `app.modules.*.manifest`.

    Best-effort: skip modules without manifest or with invalid shapes.
    """
    manifests: List[ModuleManifest] = []
    for name in _iter_subpackages("app.modules"):
        if not name.endswith(".manifest") and not name.split(".")[-1] == "manifest":
            # Try to load `<module>.manifest` explicitly
            mod_name = name.split(".")
            # only root level packages
            if len(mod_name) == 3 and mod_name[-1] != "manifest":
                maybe = name + ".manifest"
            else:
                continue
        else:
            maybe = name
        try:
            mod = import_module(maybe)
            m = getattr(mod, "MANIFEST", None)
            if m:
                if isinstance(m, ModuleManifest):
                    manifests.append(m)
                else:
                    try:
                        manifests.append(ModuleManifest.model_validate(m))
                    except Exception:
                        # invalid shape; ignore
                        pass
        except Exception:
            # no manifest in this module or import error; ignore
            continue
    return manifests

