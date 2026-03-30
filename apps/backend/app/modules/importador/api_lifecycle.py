from __future__ import annotations

from fastapi import Response

LEGACY_IMPORTADOR_SUCCESSOR = "/api/v1/importador/run-async"
LEGACY_IMPORTADOR_SUNSET = "Tue, 30 Jun 2026 00:00:00 GMT"


def mark_legacy_processing_endpoint(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_IMPORTADOR_SUNSET
    response.headers["Link"] = f'<{LEGACY_IMPORTADOR_SUCCESSOR}>; rel="successor-version"'
    response.headers["X-Importador-Legacy"] = "true"
