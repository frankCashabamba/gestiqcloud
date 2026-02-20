"""
Universal validator using canonical schemas.
Validates parsed/normalized data against document type schemas.
"""

from app.modules.imports.domain.canonical_schema import get_schema
from app.modules.imports.domain.errors import ErrorCategory, ErrorSeverity, ImportErrorCollection


class UniversalValidator:
    """Validates import items against canonical schemas."""

    def validate_document(
        self,
        data: dict,
        doc_type: str,
        row_number: int | None = None,
        item_id: str | None = None,
        batch_id: str | None = None,
    ) -> ImportErrorCollection:
        """
        Validate a document against its schema.

        Args:
            data: Normalized document data
            doc_type: Document type (e.g., 'sales_invoice', 'expense')
            row_number: Row number in source file (for error context)
            item_id: Import item ID (for linking)
            batch_id: Import batch ID (for linking)

        Returns:
            ImportErrorCollection with all validation errors
        """
        errors = ImportErrorCollection()

        schema = get_schema(doc_type)
        if not schema:
            errors.add(
                f"Unknown document type: {doc_type}",
                category=ErrorCategory.CUSTOM,
                severity=ErrorSeverity.ERROR,
                row_number=row_number,
                item_id=item_id,
                batch_id=batch_id,
                doc_type=doc_type,
            )
            return errors

        # Check required fields
        for field_name in schema.required_fields:
            if field_name not in schema.fields:
                continue

            value = data.get(field_name)
            if value is None or value == "":
                field_def = schema.fields[field_name]
                errors.add_missing_field_error(
                    field_name=field_name,
                    row_number=row_number,
                    canonical_field=field_def.canonical_name,
                )
                # Add context
                errors.errors[-1].item_id = item_id
                errors.errors[-1].batch_id = batch_id
                errors.errors[-1].doc_type = doc_type

        # Validate all present fields
        for field_name, field_def in schema.fields.items():
            value = data.get(field_name)

            if value is None or value == "":
                continue

            # Run field rules
            for rule in field_def.rules:
                is_valid, error_msg = rule.validate(value)
                if not is_valid:
                    errors.add_validation_error(
                        field_name=field_name,
                        rule_name=rule.name,
                        message=error_msg or f"Validation failed for {field_name}",
                        row_number=row_number,
                        canonical_field=field_def.canonical_name,
                        raw_value=value,
                        suggestion=self._suggest_fix(field_name, field_def.data_type, value),
                    )
                    # Add context
                    errors.errors[-1].item_id = item_id
                    errors.errors[-1].batch_id = batch_id
                    errors.errors[-1].doc_type = doc_type

        return errors

    def _suggest_fix(self, field_name: str, data_type: str, value) -> str | None:
        """Generate a suggestion for fixing a value."""
        if data_type == "number":
            return f"Ensure '{field_name}' contains only digits (and optionally . or ,)"
        elif data_type == "date":
            return f"Use format YYYY-MM-DD or DD/MM/YYYY for '{field_name}'"
        elif data_type == "decimal":
            return f"Use decimal notation for '{field_name}' (e.g., 123.45 or 123,45)"
        else:
            return None

    def validate_document_complete(
        self,
        data: dict,
        doc_type: str,
        row_number: int | None = None,
        item_id: str | None = None,
        batch_id: str | None = None,
    ) -> tuple[bool, ImportErrorCollection]:
        """
        Validate and return bool indicating if validation passed.

        Returns:
            (is_valid, errors)
        """
        errors = self.validate_document(
            data=data,
            doc_type=doc_type,
            row_number=row_number,
            item_id=item_id,
            batch_id=batch_id,
        )
        return not errors.has_errors(), errors

    def find_field_mapping(
        self,
        headers: list[str],
        doc_type: str,
    ) -> dict[str, str]:
        """
        Auto-detect field mapping from headers.
        Uses fuzzy matching: if header contains an alias keyword, it's a match.

        Args:
            headers: List of header names from source file
            doc_type: Document type

        Returns:
            Dict mapping source header -> canonical field name
        """
        schema = get_schema(doc_type)
        if not schema:
            return {}

        mapping = {}
        used_fields = set()

        # For each header, find best matching field
        for header in headers:
            header_lower = header.lower().strip()
            header_words = set(header_lower.replace("_", " ").replace("-", " ").split())

            best_match = None
            best_score = 0

            # For each field in schema, calculate match score
            for canonical_name, field_def in schema.fields.items():
                if canonical_name in used_fields:
                    continue

                score = 0

                # Exact match on canonical name
                if field_def.canonical_name.lower() == header_lower:
                    score = 100
                    best_match = canonical_name
                    break

                # Check aliases with fuzzy matching
                for alias in field_def.aliases:
                    alias_lower = alias.lower()
                    alias_words = set(alias_lower.replace("_", " ").replace("-", " ").split())

                    # Exact match
                    if alias_lower == header_lower:
                        score = 100
                        break

                    # Word overlap score
                    overlap = len(header_words & alias_words)
                    if overlap > 0:
                        score = max(score, overlap * 10)

                if score > best_score:
                    best_score = score
                    best_match = canonical_name

            if best_match and best_score > 0:
                mapping[header] = best_match
                used_fields.add(best_match)

        return mapping


# Global validator instance
universal_validator = UniversalValidator()
