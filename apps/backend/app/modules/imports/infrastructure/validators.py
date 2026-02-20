from typing import Any

from app.modules.imports.domain.interfaces import CountryRulePack, DocType, ValidatorStrategy


class StrictValidator(ValidatorStrategy):
    def __init__(self, country_pack: CountryRulePack | None = None):
        self.country_pack = country_pack
        self.required_fields = {}
        self.field_types = {}

    def register_required_fields(self, doc_type: str, fields: list[str]) -> None:
        self.required_fields[doc_type] = fields

    def register_field_types(self, doc_type: str, types: dict[str, type]) -> None:
        self.field_types[doc_type] = types

    def validate(self, data: dict[str, Any], doc_type: DocType) -> list[dict[str, str]]:
        errors = []

        doc_type_str = doc_type.value

        if doc_type_str in self.required_fields:
            for required_field in self.required_fields[doc_type_str]:
                if required_field not in data or not data[required_field]:
                    errors.append(
                        {
                            "field": required_field,
                            "error": "required_field_missing",
                        }
                    )

        if doc_type_str in self.field_types:
            for field, expected_type in self.field_types[doc_type_str].items():
                if field in data and data[field] is not None:
                    if not isinstance(data[field], expected_type):
                        errors.append(
                            {
                                "field": field,
                                "error": f"expected_type_{expected_type.__name__}",
                            }
                        )

        if self.country_pack:
            country_errors = self.country_pack.validate_fiscal_fields(data)
            errors.extend(country_errors)

        return errors


class InvoiceValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.INVOICE.value,
            ["invoice_number", "invoice_date", "amount", "tax_id"],
        )
        self.register_field_types(
            DocType.INVOICE.value,
            {
                "invoice_number": str,
                "invoice_date": str,
                "amount": (int, float),
                "tax": (int, float),
            },
        )


class ExpenseReceiptValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.EXPENSE_RECEIPT.value,
            ["amount", "invoice_date"],
        )
        self.register_field_types(
            DocType.EXPENSE_RECEIPT.value,
            {
                "amount": (int, float),
                "invoice_date": str,
            },
        )


class BankStatementValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.BANK_STATEMENT.value,
            ["account", "bank"],
        )
        self.register_field_types(
            DocType.BANK_STATEMENT.value,
            {
                "account": str,
                "bank": str,
            },
        )


class BankTransactionValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.BANK_TRANSACTION.value,
            ["amount", "concept"],
        )
        self.register_field_types(
            DocType.BANK_TRANSACTION.value,
            {
                "amount": (int, float),
                "concept": str,
            },
        )


class ProductListValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.PRODUCT_LIST.value,
            ["product", "price"],
        )
        self.register_field_types(
            DocType.PRODUCT_LIST.value,
            {
                "product": str,
                "price": (int, float),
                "stock": (int, float),
            },
        )


class RecipeValidator(StrictValidator):
    def __init__(self, country_pack: CountryRulePack | None = None):
        super().__init__(country_pack)
        self.register_required_fields(
            DocType.RECIPE.value,
            ["product"],
        )
        self.register_field_types(
            DocType.RECIPE.value,
            {
                "product": str,
            },
        )
