"""
Structured error reporting for import processing.
Each error has: row, field, rule, message, suggestion.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Any


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(str, Enum):
    """Error categories for grouping/reporting."""
    VALIDATION = "validation"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_FIELD = "missing_field"
    PARSING = "parsing"
    DUPLICATE = "duplicate"
    RANGE_VIOLATION = "range_violation"
    FORMAT = "format"
    CUSTOM = "custom"


@dataclass
class ImportError:
    """Structured error with context for debugging and user guidance."""
    
    # Location
    row_number: Optional[int] = None  # 1-based row number in file
    field_name: Optional[str] = None  # Field name in source
    canonical_field: Optional[str] = None  # Canonical field name in schema
    
    # Classification
    category: ErrorCategory = ErrorCategory.VALIDATION
    severity: ErrorSeverity = ErrorSeverity.ERROR
    rule_name: Optional[str] = None  # Which validation rule failed
    
    # Message
    message: str = ""  # Main error message
    suggestion: Optional[str] = None  # How to fix it
    raw_value: Optional[Any] = None  # The actual value that failed
    
    # Context
    item_id: Optional[str] = None  # Import item ID for linking
    batch_id: Optional[str] = None  # Import batch ID for linking
    doc_type: Optional[str] = None  # Document type being validated
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = asdict(self)
        # Convert enums to strings
        if isinstance(self.category, ErrorCategory):
            result["category"] = self.category.value
        if isinstance(self.severity, ErrorSeverity):
            result["severity"] = self.severity.value
        # Convert non-serializable raw_value
        if self.raw_value is not None:
            result["raw_value"] = str(self.raw_value)
        return result
    
    def __str__(self) -> str:
        """User-friendly error message."""
        location = ""
        if self.row_number:
            location = f"Row {self.row_number}"
        if self.field_name:
            location = f"{location} {self.field_name}" if location else self.field_name
        
        msg = f"{location}: {self.message}"
        if self.suggestion:
            msg += f"\n  → {self.suggestion}"
        return msg


class ImportErrorCollection:
    """Collection of errors from parsing/validation."""
    
    def __init__(self):
        self.errors: list[ImportError] = []
    
    def add(
        self,
        message: str,
        *,
        row_number: Optional[int] = None,
        field_name: Optional[str] = None,
        canonical_field: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.VALIDATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        rule_name: Optional[str] = None,
        suggestion: Optional[str] = None,
        raw_value: Optional[Any] = None,
        item_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> ImportError:
        """Add a new error to the collection."""
        error = ImportError(
            row_number=row_number,
            field_name=field_name,
            canonical_field=canonical_field,
            category=category,
            severity=severity,
            rule_name=rule_name,
            message=message,
            suggestion=suggestion,
            raw_value=raw_value,
            item_id=item_id,
            batch_id=batch_id,
            doc_type=doc_type,
        )
        self.errors.append(error)
        return error
    
    def add_validation_error(
        self,
        field_name: str,
        rule_name: str,
        message: str,
        row_number: Optional[int] = None,
        canonical_field: Optional[str] = None,
        suggestion: Optional[str] = None,
        raw_value: Optional[Any] = None,
    ) -> ImportError:
        """Convenience method for validation errors."""
        return self.add(
            message=message,
            row_number=row_number,
            field_name=field_name,
            canonical_field=canonical_field,
            category=ErrorCategory.VALIDATION,
            rule_name=rule_name,
            suggestion=suggestion,
            raw_value=raw_value,
        )
    
    def add_missing_field_error(
        self,
        field_name: str,
        row_number: Optional[int] = None,
        canonical_field: Optional[str] = None,
    ) -> ImportError:
        """Convenience method for missing required fields."""
        return self.add(
            message=f"Required field '{field_name}' is missing",
            row_number=row_number,
            field_name=field_name,
            canonical_field=canonical_field,
            category=ErrorCategory.MISSING_FIELD,
            severity=ErrorSeverity.ERROR,
            suggestion=f"Please provide a value for '{field_name}'",
        )
    
    def add_type_error(
        self,
        field_name: str,
        expected_type: str,
        row_number: Optional[int] = None,
        canonical_field: Optional[str] = None,
        raw_value: Optional[Any] = None,
        suggestion: Optional[str] = None,
    ) -> ImportError:
        """Convenience method for type mismatches."""
        return self.add(
            message=f"Field '{field_name}' should be {expected_type}",
            row_number=row_number,
            field_name=field_name,
            canonical_field=canonical_field,
            category=ErrorCategory.TYPE_MISMATCH,
            raw_value=raw_value,
            suggestion=suggestion or f"Provide a valid {expected_type} value",
        )
    
    def by_row(self) -> dict[Optional[int], list[ImportError]]:
        """Group errors by row number."""
        result: dict[Optional[int], list[ImportError]] = {}
        for error in self.errors:
            row = error.row_number
            if row not in result:
                result[row] = []
            result[row].append(error)
        return result
    
    def by_field(self) -> dict[Optional[str], list[ImportError]]:
        """Group errors by field name."""
        result: dict[Optional[str], list[ImportError]] = {}
        for error in self.errors:
            field = error.field_name
            if field not in result:
                result[field] = []
            result[field].append(error)
        return result
    
    def by_category(self) -> dict[ErrorCategory, list[ImportError]]:
        """Group errors by category."""
        result: dict[ErrorCategory, list[ImportError]] = {}
        for error in self.errors:
            cat = error.category
            if cat not in result:
                result[cat] = []
            result[cat].append(error)
        return result
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_errors_in_row(self, row_number: int) -> bool:
        """Check if a specific row has errors."""
        return any(e.row_number == row_number for e in self.errors)
    
    def errors_for_row(self, row_number: int) -> list[ImportError]:
        """Get all errors for a specific row."""
        return [e for e in self.errors if e.row_number == row_number]
    
    def to_list(self) -> list[dict[str, Any]]:
        """Convert all errors to list of dicts."""
        return [e.to_dict() for e in self.errors]
    
    def __len__(self) -> int:
        return len(self.errors)
    
    def __iter__(self):
        return iter(self.errors)
