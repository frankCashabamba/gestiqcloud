from __future__ import annotations

import math

from app.modules.importador.utils import json_safe


def test_json_safe_converts_non_finite_numbers_to_none_recursively():
    payload = {
        "a": math.nan,
        "b": math.inf,
        "c": -math.inf,
        "rows": [
            {"qty": 3, "price": math.nan},
            {"qty": 2, "price": 1.5},
        ],
    }

    safe = json_safe(payload)

    assert safe["a"] is None
    assert safe["b"] is None
    assert safe["c"] is None
    assert safe["rows"][0]["qty"] == 3
    assert safe["rows"][0]["price"] is None
    assert safe["rows"][1]["price"] == 1.5
