from typing import Any

from app.modules.imports.config.aliases import detect_language, normalize_field_name
from app.modules.imports.domain.interfaces import (
    DocType,
    MapperStrategy,
    MappingResult,
    ValidatorStrategy,
)


class CanonicalMapper(MapperStrategy):
    def __init__(self):
        self.validators: dict[str, ValidatorStrategy] = {}
        self.field_mappings: dict[str, dict] = {}

    def register_validator(self, doc_type: str, validator: ValidatorStrategy) -> None:
        self.validators[doc_type] = validator

    def register_field_mapping(self, doc_type: str, mapping: dict[str, str]) -> None:
        self.field_mappings[doc_type] = mapping

    def map_fields(self, raw_data: dict[str, Any], doc_type: DocType) -> MappingResult:
        language = detect_language(str(raw_data))
        mapping = self.field_mappings.get(doc_type.value, {})

        normalized_data = {}
        mapped_fields = {}
        unmapped_fields = []

        for raw_field, raw_value in raw_data.items():
            canonical_field = self._find_canonical_field(raw_field, language, mapping)

            if canonical_field:
                normalized_data[canonical_field] = raw_value
                mapped_fields[raw_field] = canonical_field
            else:
                unmapped_fields.append(raw_field)

        validation_errors = []
        warnings = []

        if doc_type.value in self.validators:
            validator = self.validators[doc_type.value]
            validation_errors = validator.validate(normalized_data, doc_type)

        return MappingResult(
            normalized_data=normalized_data,
            doc_type=doc_type,
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
            validation_errors=validation_errors,
            warnings=warnings,
        )

    def _find_canonical_field(self, raw_field: str, language: str, mapping: dict) -> str | None:
        normalized = normalize_field_name(raw_field, language)

        for canonical, aliases in mapping.items():
            if normalized in aliases or raw_field.lower() in aliases:
                return canonical

        if normalized in mapping:
            return normalized

        return None

    def add_field_alias(self, doc_type: str, canonical: str, alias: str) -> None:
        if doc_type not in self.field_mappings:
            self.field_mappings[doc_type] = {}

        if canonical not in self.field_mappings[doc_type]:
            self.field_mappings[doc_type][canonical] = []

        if not isinstance(self.field_mappings[doc_type][canonical], list):
            self.field_mappings[doc_type][canonical] = [self.field_mappings[doc_type][canonical]]

        if alias not in self.field_mappings[doc_type][canonical]:
            self.field_mappings[doc_type][canonical].append(alias)
