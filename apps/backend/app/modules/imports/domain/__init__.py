"""
Dominio del módulo de importación documental.

Incluye schema canónico SPEC-1, validadores y handlers.
"""

from __future__ import annotations

from .canonical_schema import (
    CanonicalDocument,
    TaxBreakdownItem,
    TotalsBlock,
    PartyInfo,
    DocumentLine,
    PaymentInfo,
    BankTxInfo,
    RoutingProposal,
    AttachmentInfo,
    validate_canonical,
    validate_totals,
    validate_tax_breakdown,
    build_routing_proposal,
    VALID_DOC_TYPES,
    VALID_COUNTRIES,
    VALID_CURRENCIES,
)

__all__ = [
    "CanonicalDocument",
    "TaxBreakdownItem",
    "TotalsBlock",
    "PartyInfo",
    "DocumentLine",
    "PaymentInfo",
    "BankTxInfo",
    "RoutingProposal",
    "AttachmentInfo",
    "validate_canonical",
    "validate_totals",
    "validate_tax_breakdown",
    "build_routing_proposal",
    "VALID_DOC_TYPES",
    "VALID_COUNTRIES",
    "VALID_CURRENCIES",
]
