from __future__ import annotations

import unicodedata

from .schema import HeaderNormalization


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_headers(
    raw_headers: list[str],
    config: HeaderNormalization,
    language: str = "es",
) -> list[str]:
    lang_synonyms: dict[str, list[str]] = config.synonyms.get(language, {})
    reverse_map: dict[str, str] = {}
    for canonical, aliases in lang_synonyms.items():
        for alias in aliases:
            key = alias.strip().lower()
            if config.strip_accents:
                key = _strip_accents(key)
            reverse_map[key] = canonical

    result: list[str] = []
    for raw in raw_headers:
        norm = raw.strip().lower()
        if config.strip_accents:
            norm = _strip_accents(norm)
        canonical = reverse_map.get(norm, norm)
        result.append(canonical)

    return result
