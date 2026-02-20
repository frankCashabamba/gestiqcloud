from typing import Optional

from app.modules.imports.domain.interfaces import (
    AnalyzeResult,
    ConfidenceLevel,
    DocType,
    MappingResult,
    ParseResult,
    ParserAdapter,
)


class SmartRouter:
    def __init__(self):
        self.parsers: dict[str, ParserAdapter] = {}
        self.classifiers: dict[str, any] = {}
        self.mappers: dict[str, any] = {}
        self.validators: dict[str, any] = {}

    def register_parser(self, parser_id: str, parser: ParserAdapter) -> None:
        self.parsers[parser_id] = parser

    def register_classifier(self, name: str, classifier) -> None:
        self.classifiers[name] = classifier

    def register_mapper(self, name: str, mapper) -> None:
        self.mappers[name] = mapper

    def register_validator(self, name: str, validator) -> None:
        self.validators[name] = validator

    def ingest(
        self,
        file_path: str,
        hinted_doc_type: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ParseResult:
        parser = self._select_parser(file_path, content_type, hinted_doc_type)
        if not parser:
            return self._create_empty_parse_result(file_path)

        return parser.parse(file_path)

    def classify(self, raw_data: dict, parser_id: str) -> AnalyzeResult:
        classifier = self.classifiers.get("hybrid")
        if not classifier:
            return self._default_classify(raw_data)

        return classifier.classify(raw_data)

    def map(self, raw_data: dict, doc_type: DocType) -> MappingResult:
        mapper = self.mappers.get("canonical")
        if not mapper:
            return self._default_map(raw_data, doc_type)

        return mapper.map_fields(raw_data, doc_type)

    def validate(self, data: dict, doc_type: DocType) -> list[dict]:
        validator = self.validators.get("strict")
        if not validator:
            return []

        return validator.validate(data, doc_type)

    def promote(
        self,
        analyze_result: AnalyzeResult,
        mapping_result: MappingResult,
    ) -> tuple[bool, Optional[str]]:
        if analyze_result.confidence == ConfidenceLevel.HIGH:
            validation_errors = self.validate(
                mapping_result.normalized_data, analyze_result.doc_type
            )
            if validation_errors:
                return False, "validation_failed"
            return True, None

        if analyze_result.confidence == ConfidenceLevel.MEDIUM:
            return False, "needs_review"

        return False, "confidence_too_low"

    def _select_parser(
        self, file_path: str, content_type: Optional[str], hinted_doc_type: Optional[str]
    ) -> Optional[ParserAdapter]:
        for parser in self.parsers.values():
            if parser.can_parse(file_path, content_type):
                return parser
        return None

    def _default_classify(self, raw_data: dict) -> AnalyzeResult:
        return AnalyzeResult(
            doc_type=DocType.GENERIC,
            confidence=ConfidenceLevel.LOW,
            confidence_score=0.0,
            raw_data=raw_data,
            errors=[],
            metadata={},
        )

    def _default_map(self, raw_data: dict, doc_type: DocType) -> MappingResult:
        return MappingResult(
            normalized_data=raw_data,
            doc_type=doc_type,
            mapped_fields={},
            unmapped_fields=list(raw_data.keys()),
            validation_errors=[],
            warnings=[],
        )

    def _create_empty_parse_result(self, file_path: str) -> ParseResult:
        return ParseResult(
            items=[],
            doc_type=DocType.GENERIC,
            metadata={"file_path": file_path},
            parse_errors=[{"error": "no_parser_found"}],
        )
