"""Extractor heurístico para documentos procesados con OCR."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.imports.extractores.utilidades import (
    correct_ocr_errors,
    find_tax_id,
    search_amount,
    search_client,
    search_concept,
    search_date,
    search_description,
    search_invoice_number,
    search_issuer,
    search_subtotal,
)
from app.modules.imports.services.ocr_service import DocumentLayout, OCRResult

logger = logging.getLogger("imports.ocr_extractor")


@dataclass
class ExtractedInvoice:
    """Datos extraídos de factura."""

    invoice_number: str | None = None
    date: str | None = None
    vendor: str | None = None
    vendor_tax_id: str | None = None
    customer: str | None = None
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    concept: str | None = None
    confidence: float = 0.0
    raw_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedReceipt:
    """Datos extraídos de recibo."""

    date: str | None = None
    total: float = 0.0
    payment_method: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)
    merchant: str | None = None
    confidence: float = 0.0
    raw_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedBankTransaction:
    """Transacción bancaria extraída."""

    date: str | None = None
    description: str | None = None
    amount: float = 0.0
    balance: float | None = None
    reference: str | None = None
    transaction_type: str | None = None


@dataclass
class ExtractedBankStatement:
    """Datos extraídos de extracto bancario."""

    account_number: str | None = None
    iban: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    transactions: list[ExtractedBankTransaction] = field(default_factory=list)
    confidence: float = 0.0
    raw_fields: dict[str, Any] = field(default_factory=dict)


class OCRExtractor:
    """Extractor heurístico basado en layout detectado por OCR."""

    def __init__(self) -> None:
        self.logger = logger

    def extract(self, ocr_result: OCRResult) -> dict[str, Any]:
        """
        Extrae datos estructurados del resultado OCR según el layout.

        Args:
            ocr_result: Resultado del servicio OCR

        Returns:
            Diccionario con datos extraídos según el tipo de documento
        """
        text = correct_ocr_errors(ocr_result.text)

        if ocr_result.layout == DocumentLayout.INVOICE:
            invoice = self._extract_invoice(text, ocr_result)
            return {
                "doc_type": "invoice",
                "data": invoice.__dict__,
                "confidence": invoice.confidence,
            }

        if ocr_result.layout == DocumentLayout.RECEIPT:
            receipt = self._extract_receipt(text, ocr_result)
            return {
                "doc_type": "receipt",
                "data": receipt.__dict__,
                "confidence": receipt.confidence,
            }

        if ocr_result.layout == DocumentLayout.BANK_STATEMENT:
            statement = self._extract_bank_statement(text, ocr_result)
            return {
                "doc_type": "bank_statement",
                "data": statement.__dict__,
                "confidence": statement.confidence,
            }

        if ocr_result.layout == DocumentLayout.TICKET_POS:
            ticket = self._extract_ticket_pos(text, ocr_result)
            return {
                "doc_type": "ticket_pos",
                "data": ticket,
                "confidence": ticket.get("confidence", 0.65),
            }

        if ocr_result.layout == DocumentLayout.TABLE and ocr_result.tables:
            return {
                "doc_type": "table",
                "data": {
                    "tables": ocr_result.tables,
                    "table_count": len(ocr_result.tables),
                },
                "confidence": ocr_result.confidence,
            }

        return {
            "doc_type": "unknown",
            "data": {
                "text": text[:5000],
                "text_length": len(text),
            },
            "confidence": ocr_result.confidence * 0.5,
        }

    def _extract_invoice(self, text: str, ocr_result: OCRResult) -> ExtractedInvoice:
        """Extrae datos de factura."""
        invoice = ExtractedInvoice()

        invoice.invoice_number = search_invoice_number(text)
        invoice.date = search_date(text)
        invoice.vendor = search_issuer(text)
        invoice.vendor_tax_id = find_tax_id(text)
        invoice.customer = search_client(text)
        invoice.concept = search_concept(text) or search_description(text)

        total_str = search_amount(text)
        if total_str:
            try:
                invoice.total = float(total_str.replace(",", "."))
            except ValueError:
                pass

        subtotal_str = search_subtotal(text)
        if subtotal_str:
            try:
                invoice.subtotal = float(subtotal_str.replace(",", "."))
            except ValueError:
                if invoice.total > 0:
                    invoice.subtotal = invoice.total / 1.12

        if invoice.subtotal > 0 and invoice.total > 0:
            invoice.tax = invoice.total - invoice.subtotal

        invoice.currency = self._detect_currency(text)

        fields_found = sum(
            [
                bool(invoice.invoice_number),
                bool(invoice.date),
                bool(invoice.vendor or invoice.vendor_tax_id),
                invoice.total > 0,
            ]
        )
        invoice.confidence = min(0.95, (fields_found / 4) * ocr_result.confidence)

        invoice.raw_fields = {
            "ocr_confidence": ocr_result.confidence,
            "layout": ocr_result.layout.value,
        }

        return invoice

    def _extract_receipt(self, text: str, ocr_result: OCRResult) -> ExtractedReceipt:
        """Extrae datos de recibo."""
        receipt = ExtractedReceipt()

        receipt.date = search_date(text)

        total_str = search_amount(text)
        if total_str:
            try:
                receipt.total = float(total_str.replace(",", "."))
            except ValueError:
                pass

        receipt.merchant = search_issuer(text)
        receipt.payment_method = self._detect_payment_method(text)
        receipt.items = self._extract_receipt_items(text)

        fields_found = sum(
            [
                bool(receipt.date),
                receipt.total > 0,
                bool(receipt.merchant),
                len(receipt.items) > 0,
            ]
        )
        receipt.confidence = min(0.90, (fields_found / 4) * ocr_result.confidence)

        receipt.raw_fields = {
            "ocr_confidence": ocr_result.confidence,
            "layout": ocr_result.layout.value,
        }

        return receipt

    def _extract_bank_statement(self, text: str, ocr_result: OCRResult) -> ExtractedBankStatement:
        """Extrae datos de extracto bancario."""
        statement = ExtractedBankStatement()

        iban_match = re.search(r"[A-Z]{2}\d{2}[A-Z0-9]{4,30}", text)
        if iban_match:
            statement.iban = iban_match.group(0)

        account_match = re.search(r"(?:cuenta|account)[:\s]*(\d{10,20})", text, re.I)
        if account_match:
            statement.account_number = account_match.group(1)

        statement.transactions = self._extract_bank_transactions(text, ocr_result)

        if ocr_result.tables:
            for table in ocr_result.tables:
                table_transactions = self._extract_transactions_from_table(table)
                statement.transactions.extend(table_transactions)

        balance_match = re.search(
            r"(?:saldo|balance)[:\s]*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", text, re.I
        )
        if balance_match:
            try:
                statement.closing_balance = float(balance_match.group(1).replace(",", "."))
            except ValueError:
                pass

        fields_found = sum(
            [
                bool(statement.iban or statement.account_number),
                len(statement.transactions) > 0,
                statement.closing_balance is not None,
            ]
        )
        statement.confidence = min(0.85, (fields_found / 3) * ocr_result.confidence)

        statement.raw_fields = {
            "ocr_confidence": ocr_result.confidence,
            "layout": ocr_result.layout.value,
            "tables_found": len(ocr_result.tables),
        }

        return statement

    def _extract_bank_transactions(
        self, text: str, ocr_result: OCRResult
    ) -> list[ExtractedBankTransaction]:
        """Extrae transacciones del texto."""
        transactions: list[ExtractedBankTransaction] = []

        date_pattern = r"(\d{2}[/-]\d{2}[/-]\d{2,4})"
        amount_pattern = r"(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))"

        lines = text.split("\n")
        for line in lines:
            date_match = re.search(date_pattern, line)
            amount_matches = re.findall(amount_pattern, line)

            if date_match and amount_matches:
                tx = ExtractedBankTransaction()
                tx.date = date_match.group(1)

                try:
                    tx.amount = float(amount_matches[-1].replace(",", "."))
                except ValueError:
                    continue

                desc_start = date_match.end()
                desc_end = line.rfind(amount_matches[-1])
                if desc_end > desc_start:
                    tx.description = line[desc_start:desc_end].strip()

                if len(amount_matches) > 1:
                    try:
                        tx.balance = float(amount_matches[0].replace(",", "."))
                    except ValueError:
                        pass

                transactions.append(tx)

        return transactions

    def _extract_transactions_from_table(
        self, table: list[list[str]]
    ) -> list[ExtractedBankTransaction]:
        """Extrae transacciones de una tabla detectada."""
        transactions: list[ExtractedBankTransaction] = []

        if len(table) < 2:
            return transactions

        headers = [str(h).lower() for h in table[0]]

        date_col = next((i for i, h in enumerate(headers) if "fecha" in h or "date" in h), None)
        desc_col = next(
            (
                i
                for i, h in enumerate(headers)
                if "concepto" in h or "descripcion" in h or "description" in h
            ),
            None,
        )
        amount_col = next(
            (i for i, h in enumerate(headers) if "importe" in h or "monto" in h or "amount" in h),
            None,
        )
        balance_col = next(
            (i for i, h in enumerate(headers) if "saldo" in h or "balance" in h), None
        )

        for row in table[1:]:
            if len(row) <= max(
                filter(None, [date_col, desc_col, amount_col, balance_col]), default=0
            ):
                continue

            tx = ExtractedBankTransaction()

            if date_col is not None and date_col < len(row):
                tx.date = str(row[date_col]).strip() or None

            if desc_col is not None and desc_col < len(row):
                tx.description = str(row[desc_col]).strip() or None

            if amount_col is not None and amount_col < len(row):
                try:
                    tx.amount = float(str(row[amount_col]).replace(",", "."))
                except ValueError:
                    continue

            if balance_col is not None and balance_col < len(row):
                try:
                    tx.balance = float(str(row[balance_col]).replace(",", "."))
                except ValueError:
                    pass

            if tx.date or tx.amount != 0:
                transactions.append(tx)

        return transactions

    def _extract_receipt_items(self, text: str) -> list[dict[str, Any]]:
        """Extrae items de un recibo."""
        items: list[dict[str, Any]] = []

        item_pattern = r"(\d+)\s*[xX]\s*(.+?)\s+(\d{1,3}(?:[.,]\d{2}))"
        matches = re.findall(item_pattern, text)

        for qty, desc, price in matches:
            try:
                items.append(
                    {
                        "quantity": int(qty),
                        "description": desc.strip(),
                        "price": float(price.replace(",", ".")),
                    }
                )
            except ValueError:
                continue

        return items

    def _detect_currency(self, text: str) -> str:
        """Detecta la moneda del documento."""
        currency_patterns = [
            (r"\$\s*\d", "USD"),
            (r"€\s*\d", "EUR"),
            (r"\bUSD\b", "USD"),
            (r"\bEUR\b", "EUR"),
            (r"\bMXN\b", "MXN"),
            (r"\bCOP\b", "COP"),
            (r"\bPEN\b", "PEN"),
        ]

        for pattern, currency in currency_patterns:
            if re.search(pattern, text, re.I):
                return currency

        return "USD"

    def _detect_payment_method(self, text: str) -> str | None:
        """Detecta el método de pago."""
        methods = [
            (r"\b(visa|mastercard|amex|american express)\b", "card"),
            (r"\b(efectivo|cash)\b", "cash"),
            (r"\b(paypal)\b", "paypal"),
            (r"\b(transferencia|transfer)\b", "transfer"),
            (r"\b(debito|debit)\b", "debit"),
            (r"\b(credito|credit)\b", "credit"),
        ]

        text_lower = text.lower()
        for pattern, method in methods:
            if re.search(pattern, text_lower):
                return method

        return None

    def _extract_ticket_pos(self, text: str, ocr_result: OCRResult) -> dict:
        """Extrae datos de ticket POS térmico."""
        from app.modules.imports.extractores.extractor_ticket import extraer_ticket

        resultados = extraer_ticket(text, country="EC")

        if resultados:
            result = resultados[0]
            result["ocr_confidence"] = ocr_result.confidence
            result["layout"] = ocr_result.layout.value
            return result

        return {
            "doc_type": "ticket_pos",
            "text": text[:2000],
            "confidence": 0.3,
            "ocr_confidence": ocr_result.confidence,
        }


ocr_extractor = OCRExtractor()
