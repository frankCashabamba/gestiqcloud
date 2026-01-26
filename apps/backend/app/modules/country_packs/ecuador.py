from __future__ import annotations

import unicodedata
from decimal import Decimal

from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import BuyerInfo, SaleDraft, TaxLine, _q2
from app.modules.documents.domain.validation import ValidationError


class EcuadorPack:
    countryCode = "EC"
    version = "1.0.0"

    def decide_document_type(self, input: SaleDraft, cfg: TenantDocConfig) -> str:
        allowed = {"TICKET_NO_FISCAL", "FACTURA", "NOTA_VENTA"}
        desired = (cfg.document_mode_default or "").strip().upper()
        if desired not in allowed:
            desired = ""
        # Default behavior: identified buyer → FACTURA; consumer final → ticket
        if input.buyer.mode == "IDENTIFIED":
            return desired or "FACTURA"
        return desired or "TICKET_NO_FISCAL"

    def validate(self, input: SaleDraft, cfg: TenantDocConfig) -> list[ValidationError]:
        errs: list[ValidationError] = []
        policy = cfg.buyer_policy or {}
        if cfg.id_types and input.buyer.mode == "IDENTIFIED":

            def normalize(value: str) -> str:
                cleaned = "".join(
                    ch
                    for ch in unicodedata.normalize("NFD", value or "")
                    if not unicodedata.combining(ch)
                )
                # Remove whitespace/punctuation so "C.I." and "CI" match.
                cleaned = "".join(ch for ch in cleaned if ch.isalnum())
                return cleaned.strip().upper()

            allowed = {normalize(t) for t in cfg.id_types if t}
            if normalize(input.buyer.idType) not in allowed:
                errs.append(
                    ValidationError(
                        code="invalid_id_type",
                        message="Buyer idType not allowed for country",
                        field="buyer.idType",
                    )
                )
        if input.buyer.mode == "CONSUMER_FINAL":
            max_total = Decimal(str(policy.get("consumerFinalMaxTotal", "0")))
            require = bool(policy.get("requireBuyerAboveAmount", False))
            if require and max_total > 0:
                total = sum((item.qty * item.unitPrice) - item.discount for item in input.items)
                if total > max_total:
                    errs.append(
                        ValidationError(
                            code="buyer_required",
                            message="Buyer data required above max total",
                            field="buyer",
                        )
                    )
        return errs

    def build_buyer(self, input: SaleDraft, cfg: TenantDocConfig) -> BuyerInfo:
        if input.buyer.mode == "CONSUMER_FINAL":
            return BuyerInfo(
                mode="CONSUMER_FINAL",
                idType="NONE",
                idNumber="9999999999999",
                name=input.buyer.name or "CONSUMIDOR FINAL",
            )
        return BuyerInfo(
            mode="IDENTIFIED",
            idType=input.buyer.idType,
            idNumber=input.buyer.idNumber,
            name=input.buyer.name,
        )

    def calculate_line_taxes(
        self, *, line_subtotal: Decimal, tax_category: str, cfg: TenantDocConfig
    ) -> list[TaxLine]:
        profile = cfg.tax_profile or {}
        rule = profile.get(tax_category) or profile.get("DEFAULT") or {}
        rate = Decimal(str(rule.get("rate", "0")))
        if rate > 1:
            rate = rate / 100
        if rate < 0:
            rate = Decimal("0")
        amount = _q2(line_subtotal * rate)
        code = str(rule.get("code", "0"))
        if code and code != "0":
            return [TaxLine(tax="IVA", rate=rate, amount=amount, code=code)]
        # Try to resolve code from country tax catalog (by rate)
        if cfg.tax_codes:
            for k, v in cfg.tax_codes.items():
                if v.get("rate") is None:
                    continue
                if Decimal(str(v.get("rate"))) == rate:
                    code = k
                    break
        return [TaxLine(tax="IVA", rate=rate, amount=amount, code=code)]
