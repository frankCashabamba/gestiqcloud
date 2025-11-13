from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def _to_iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # try ISO first
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        pass
    # dd/mm/yyyy or dd-mm-yyyy
    for sep in ("/", "-"):
        parts = s.split(sep)
        if (
            len(parts) == 3
            and len(parts[0]) in (1, 2)
            and len(parts[1]) in (1, 2)
            and len(parts[2]) == 4
        ):
            try:
                d, m, y = map(int, parts)
                return datetime(y, m, d).date().isoformat()
            except Exception:
                pass
    return None


def apply_mapping(
    raw: Dict[str, Any],
    mappings: Dict[str, str] | None,
    transforms: Dict[str, Any] | None,
    defaults: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Map input `raw` fields into a normalized dict.

    - `mappings`: {'dest_field': 'source_field'}
    - `transforms`: {'field': 'date' | {'type': 'date'}} for basic date normalization
    - `defaults`: fallback values when mapped source is missing/empty
    """
    mappings = mappings or {}
    transforms = transforms or {}
    defaults = defaults or {}

    normalized: Dict[str, Any] = {}

    # 1) apply mappings
    for dest, src in mappings.items():
        value = raw.get(src)
        normalized[dest] = value

    # 2) apply defaults for missing or empty
    for k, v in defaults.items():
        if normalized.get(k) in (None, ""):
            normalized[k] = v

    # 3) basic transforms (dates for now)
    for field, spec in transforms.items():
        if field not in normalized:
            continue
        kind = spec["type"] if isinstance(spec, dict) else spec
        if kind == "date":
            iso = _to_iso_date(normalized.get(field))
            if iso:
                normalized[field] = iso

    return normalized
