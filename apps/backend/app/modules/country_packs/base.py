from __future__ import annotations

from typing import Protocol

from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import BuyerInfo, SaleDraft, TaxLine
from app.modules.documents.domain.validation import ValidationError


class CountryPack(Protocol):
    countryCode: str
    version: str

    def decide_document_type(self, input: SaleDraft, cfg: TenantDocConfig) -> str: ...

    def validate(self, input: SaleDraft, cfg: TenantDocConfig) -> list[ValidationError]: ...

    def build_buyer(self, input: SaleDraft, cfg: TenantDocConfig) -> BuyerInfo: ...

    def calculate_line_taxes(
        self, *, line_subtotal, tax_category: str, cfg: TenantDocConfig
    ) -> list[TaxLine]: ...
