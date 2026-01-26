from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from app.modules.country_packs.ecuador import EcuadorPack
from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import (
    DocumentInfo,
    DocumentLine,
    DocumentModel,
    PaymentIn,
    RenderInfo,
    SaleDraft,
    SellerInfo,
    Totals,
    _q2,
)


class DocumentOrchestrator:
    """Core draft/issue pipeline (MVP)."""

    def __init__(self, *, template_id: str = "tpl_ticket_80mm", template_version: int = 1):
        self.template_id = template_id
        self.template_version = template_version
        self.country_pack = EcuadorPack()

    def draft(self, sale: SaleDraft, cfg: TenantDocConfig, seller: SellerInfo) -> DocumentModel:
        return self._build_document(sale, cfg=cfg, seller=seller, status="DRAFT", issued_at=None)

    def issue(
        self,
        sale: SaleDraft,
        cfg: TenantDocConfig,
        seller: SellerInfo,
        *,
        series: str | None,
        sequential: str | None,
    ) -> DocumentModel:
        issued_at = datetime.now(UTC)
        return self._build_document(
            sale,
            cfg=cfg,
            seller=seller,
            status="ISSUED",
            issued_at=issued_at,
            series=series,
            sequential=sequential,
        )

    def _build_document(
        self,
        sale: SaleDraft,
        *,
        cfg: TenantDocConfig,
        seller: SellerInfo,
        status: str,
        issued_at: datetime | None,
        series: str | None = None,
        sequential: str | None = None,
    ) -> DocumentModel:
        errors = self.country_pack.validate(sale, cfg)
        if errors:
            raise ValueError([e.model_dump() for e in errors])

        doc_id = str(uuid4())
        if status != "ISSUED":
            series = None
            sequential = None

        lines: list[DocumentLine] = []
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")

        for item in sale.items:
            line_subtotal = (item.qty * item.unitPrice) - item.discount
            line_subtotal = _q2(line_subtotal)
            discount_total += item.discount
            tax_lines = self.country_pack.calculate_line_taxes(
                line_subtotal=line_subtotal, tax_category=item.taxCategory, cfg=cfg
            )
            line_tax_total = sum((t.amount for t in tax_lines), Decimal("0"))
            line_total = _q2(line_subtotal + line_tax_total)
            subtotal += line_subtotal
            tax_total += line_tax_total
            lines.append(
                DocumentLine(
                    name=item.name,
                    qty=item.qty,
                    unitPrice=item.unitPrice,
                    lineSubtotal=line_subtotal,
                    taxLines=tax_lines,
                    lineTotal=line_total,
                )
            )

        totals = Totals(
            subtotal=_q2(subtotal),
            discount=_q2(discount_total),
            taxTotal=_q2(tax_total),
            grandTotal=_q2(subtotal + tax_total),
        )

        buyer = self.country_pack.build_buyer(sale, cfg)
        doc_type = self.country_pack.decide_document_type(sale, cfg)

        document = DocumentInfo(
            id=doc_id,
            type=doc_type,  # type: ignore[arg-type]
            country=sale.country,
            status=status,  # type: ignore[arg-type]
            issuedAt=issued_at,
            series=series,
            sequential=sequential,
            currency=sale.currency,
            meta={"configEffectiveFrom": cfg.effective_from, "configVersion": cfg.config_version},
        )

        render = RenderInfo(
            templateId=self.template_id,
            templateVersion=self.template_version,
            format=cfg.render_format_default,  # type: ignore[arg-type]
            locale=cfg.locale,
            configEffectiveFrom=cfg.effective_from,
        )

        return DocumentModel(
            document=document,
            seller=seller,
            buyer=buyer,
            lines=lines,
            totals=totals,
            payments=[PaymentIn(method=p.method, amount=p.amount) for p in sale.payments],
            render=render,
        )
