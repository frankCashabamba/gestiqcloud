from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, Tuple


_lock = threading.Lock()
_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
_dur_sum_ms: Dict[Tuple[str, str, int], int] = defaultdict(int)


def record(method: str, path: str, status: int, dur_ms: int) -> None:
    key = (method.upper(), path, int(status))
    with _lock:
        _counts[key] += 1
        _dur_sum_ms[key] += max(0, int(dur_ms))


def snapshot() -> Tuple[Dict[Tuple[str, str, int], int], Dict[Tuple[str, str, int], int]]:
    with _lock:
        # devuelve copias del estado actual
        return dict(_counts), dict(_dur_sum_ms)

