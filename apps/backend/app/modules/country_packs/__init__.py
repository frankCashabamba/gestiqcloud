"""Country packs registry."""

from __future__ import annotations

from collections.abc import Callable

from app.modules.country_packs.base import CountryPack
from app.modules.country_packs.ecuador import EcuadorPack
from app.modules.country_packs.espana import EspanaPack

_REGISTRY: dict[str, Callable[[], CountryPack]] = {
    "EC": EcuadorPack,
    "ES": EspanaPack,
}


def get_country_pack(country_code: str) -> CountryPack:
    """Return a country pack instance for ``country_code`` (fail-closed)."""
    code = (country_code or "").strip().upper()
    factory = _REGISTRY.get(code)
    if factory is None:
        raise ValueError("documents_country_not_supported")
    return factory()


def supported_countries() -> list[str]:
    return sorted(_REGISTRY.keys())


__all__ = [
    "CountryPack",
    "EcuadorPack",
    "EspanaPack",
    "get_country_pack",
    "supported_countries",
]
