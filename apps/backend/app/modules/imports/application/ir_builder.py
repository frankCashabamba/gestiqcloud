from __future__ import annotations

import hashlib
import unicodedata
from typing import Any

from app.modules.imports.config.aliases import detect_language


def _norm_header(h: str) -> str:
    h = unicodedata.normalize("NFKD", str(h)).encode("ascii", "ignore").decode()
    return h.strip().lower().replace(" ", "_")


class IRBuilder:

    def build_from_excel(
        self,
        file_path: str,
        file_sha256: str,
        sheet_data: list[dict],
    ) -> list[dict]:
        items: list[dict] = []
        for entry in sheet_data:
            sheet_name = entry.get("sheet", "")
            headers_raw: list[str] = [str(h) for h in entry.get("headers", [])]
            headers_norm = [_norm_header(h) for h in headers_raw]
            rows: list[dict] = entry.get("rows", [])

            sample_text = " ".join(headers_raw)
            lang = detect_language(sample_text)

            for row_idx, row in enumerate(rows):
                ir: dict[str, Any] = {
                    "source": {
                        "file_sha256": file_sha256,
                        "origin": "excel",
                        "sheet": sheet_name,
                        "row": row_idx + 1,
                    },
                    "language": lang,
                    "artifacts_ref": {},
                    "tables": [
                        {
                            "headers_raw": headers_raw,
                            "headers_norm": headers_norm,
                            "rows": [row],
                        }
                    ],
                    "text": "",
                    "kv": {},
                }
                items.append(ir)
        return items

    def build_from_ocr(
        self,
        ocr_text: str,
        file_sha256: str,
        ocr_job_id: str,
        page_no: int,
        attachment_ids: list[str] | None = None,
    ) -> dict:
        lang = detect_language(ocr_text)
        kv = self._extract_kv(ocr_text)
        return {
            "source": {
                "file_sha256": file_sha256,
                "origin": "pdf_ocr",
                "page": page_no,
            },
            "language": lang,
            "artifacts_ref": {
                "ocr_job_id": ocr_job_id,
                "attachment_ids": attachment_ids or [],
            },
            "tables": [],
            "text": ocr_text,
            "kv": kv,
        }

    def build_from_rows(
        self,
        rows: list[dict],
        origin: str = "api",
    ) -> list[dict]:
        items: list[dict] = []
        for idx, row in enumerate(rows):
            sample = " ".join(str(v) for v in row.values())
            lang = detect_language(sample)
            headers_raw = list(row.keys())
            headers_norm = [_norm_header(h) for h in headers_raw]
            ir: dict[str, Any] = {
                "source": {
                    "file_sha256": "",
                    "origin": origin,
                    "row": idx + 1,
                },
                "language": lang,
                "artifacts_ref": {},
                "tables": [
                    {
                        "headers_raw": headers_raw,
                        "headers_norm": headers_norm,
                        "rows": [row],
                    }
                ],
                "text": "",
                "kv": {},
            }
            items.append(ir)
        return items

    @staticmethod
    def detect_language(text: str) -> str:
        return detect_language(text)

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def _extract_kv(text: str) -> dict[str, str]:
        import re

        kv: dict[str, str] = {}
        ruc_match = re.search(r"RUC[:\s]*(\d{11,13})", text, re.IGNORECASE)
        if ruc_match:
            kv["RUC"] = ruc_match.group(1)
        return kv
