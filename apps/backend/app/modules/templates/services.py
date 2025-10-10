from __future__ import annotations

import json
from typing import Any, Dict


def _json_size_bytes(d: Dict[str, Any]) -> int:
    try:
        return len(json.dumps(d, ensure_ascii=False).encode("utf-8"))
    except Exception:
        return 10**9


def _depth(d: Any) -> int:
    if not isinstance(d, dict):
        return 0
    if not d:
        return 1
    return 1 + max((_depth(v) for v in d.values()), default=0)


def validate_overlay(config: Dict[str, Any], limits: Dict[str, Any]) -> None:
    max_fields = int(limits.get("max_fields", 15))
    max_bytes = int(limits.get("max_bytes", 8192))
    max_depth = int(limits.get("max_depth", 2))

    # Count fields (shallow)
    field_count = 0
    def count_fields(obj: Any) -> None:
        nonlocal field_count
        if isinstance(obj, dict):
            field_count += len(obj)
            for v in obj.values():
                count_fields(v)
        elif isinstance(obj, list):
            for v in obj:
                count_fields(v)
    count_fields(config)

    if field_count > max_fields:
        raise ValueError(f"overlay_fields_exceeded:{field_count}>{max_fields}")
    if _json_size_bytes(config) > max_bytes:
        raise ValueError("overlay_bytes_exceeded")
    if _depth(config) > max_depth:
        raise ValueError("overlay_depth_exceeded")


def deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

