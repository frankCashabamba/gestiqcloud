from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocType(str, Enum):
    INVOICE = "invoice"
    EXPENSE_RECEIPT = "expense_receipt"
    BANK_STATEMENT = "bank_statement"
    BANK_TRANSACTION = "bank_transaction"
    PRODUCT_LIST = "product_list"
    RECIPE = "recipe"
    GENERIC = "generic"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ItemStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    PROMOTED = "promoted"
    REJECTED = "rejected"


@dataclass
class AnalyzeResult:
    doc_type: DocType
    confidence: ConfidenceLevel
    confidence_score: float
    raw_data: dict[str, Any]
    errors: list[dict[str, str]]
    metadata: dict[str, Any]
    fingerprint: str | None = None


@dataclass
class MappingResult:
    normalized_data: dict[str, Any]
    doc_type: DocType
    mapped_fields: dict[str, str]
    unmapped_fields: list[str]
    validation_errors: list[dict[str, str]]
    warnings: list[dict[str, str]]


@dataclass
class ParseResult:
    items: list[dict[str, Any]]
    doc_type: DocType
    metadata: dict[str, Any]
    parse_errors: list[dict[str, str]]


class ParserAdapter(ABC):
    @abstractmethod
    def can_parse(self, file_path: str, content_type: str | None = None) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        pass

    @abstractmethod
    def get_doc_type(self) -> DocType:
        pass

    @abstractmethod
    def get_parser_id(self) -> str:
        pass


class ClassifierStrategy(ABC):
    @abstractmethod
    def classify(self, raw_data: dict[str, Any]) -> AnalyzeResult:
        pass


class ValidatorStrategy(ABC):
    @abstractmethod
    def validate(self, data: dict[str, Any], doc_type: DocType) -> list[dict[str, str]]:
        pass


class MapperStrategy(ABC):
    @abstractmethod
    def map_fields(self, raw_data: dict[str, Any], doc_type: DocType) -> MappingResult:
        pass


class CountryRulePack(ABC):
    @abstractmethod
    def get_country_code(self) -> str:
        pass

    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> tuple[bool, str | None]:
        pass

    @abstractmethod
    def validate_date_format(self, date_str: str) -> tuple[bool, str | None]:
        pass

    @abstractmethod
    def get_currency(self) -> str:
        pass

    @abstractmethod
    def get_field_aliases(self) -> dict[str, list[str]]:
        pass

    @abstractmethod
    def validate_fiscal_fields(self, data: dict[str, Any]) -> list[dict[str, str]]:
        pass


class LearningStore(ABC):
    @abstractmethod
    def record_correction(
        self,
        batch_id: str,
        item_idx: int,
        original_doc_type: DocType,
        corrected_doc_type: DocType,
        confidence_was: float,
    ) -> None:
        pass

    @abstractmethod
    def get_misclassification_stats(self) -> dict[str, int]:
        pass

    @abstractmethod
    def get_fingerprint_dataset(self) -> list[dict[str, Any]]:
        pass
