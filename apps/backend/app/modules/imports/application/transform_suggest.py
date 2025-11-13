from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any, Dict, List, Tuple

_SYN_PATH = os.path.join(
    os.path.dirname(__file__),
    "synonyms_es.json",
)


def _load_synonyms() -> Dict[str, List[str]]:
    try:
        with open(_SYN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Fallback minimal set
        return {
            "name": ["nombre", "producto", "name", "descripcion", "description", "articulo", "artículo"],
            "sku": ["sku", "codigo", "código", "code", "referencia", "ref"],
            "price": ["precio", "price", "venta", "pvp", "unitario"],
            "stock": ["stock", "cantidad", "qty", "existencia"],
            "unit": ["unidad", "uom", "u/m", "unit"],
            "category": ["categoria", "categoría", "category", "clase", "familia"],
            "image_url": ["foto", "imagen", "image", "url imagen", "url"],
            "packs": ["bultos", "packs", "cajas"],
            "units_per_pack": ["cantidad por bulto", "unidades por bulto", "u x bulto", "u x pack", "cantidad x bulto"],
            "pack_price": ["precio por bulto", "precio bulto", "precio caja"],
        }


_SYN = _load_synonyms()


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    return s


def _score(header: str, target: str, syns: List[str]) -> int:
    h = _norm(header)
    best = 0
    for w in syns:
        wnorm = _norm(w)
        if wnorm and wnorm in h:
            # longer matches score higher
            best = max(best, len(wnorm))
    return best


def suggest_mapping(headers: List[str]) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    mapping: Dict[str, str] = {}
    confidence: Dict[str, float] = {}

    # Assign each header to the best canonical field based on synonyms
    for h in headers:
        best_field = None
        best_score = 0
        for field, syns in _SYN.items():
            sc = _score(h, field, syns)
            if sc > best_score:
                best_score = sc
                best_field = field
        if best_field and best_score > 0:
            mapping[h] = best_field
            # Normalize to [0..1] simple ratio by header length
            confidence[h] = min(1.0, best_score / max(3, len(_norm(h))))

    # Transforms suggestion (price/unit and stock from packs)
    rev = {v: k for k, v in mapping.items()}
    transforms: Dict[str, Any] = {}
    if "pack_price" in rev and "units_per_pack" in rev:
        transforms["price"] = {
            "expr": "coalesce(price, pack_price / nullif(units_per_pack,0))",
            "type": "number",
            "round": 2,
        }
    if "packs" in rev and "units_per_pack" in rev:
        transforms["stock"] = {
            "expr": "coalesce(stock, packs * units_per_pack)",
            "type": "number",
        }
    transforms["unit"] = {"expr": "coalesce(unit, unidad, 'unit')"}

    defaults = {"category": "SIN_CATEGORIA"}
    return mapping, transforms, defaults, confidence

