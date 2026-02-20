from typing import Optional

from app.modules.imports.domain.interfaces import DocType, ParseResult, ParserAdapter


class BaseParserAdapter(ParserAdapter):
    def __init__(self, parser_id: str, doc_type: DocType, parser_func):
        self._parser_id = parser_id
        self._doc_type = doc_type
        self._parser_func = parser_func

    def get_parser_id(self) -> str:
        return self._parser_id

    def get_doc_type(self) -> DocType:
        return self._doc_type

    def can_parse(self, file_path: str, content_type: Optional[str] = None) -> bool:
        return self._can_parse_impl(file_path, content_type)

    def parse(self, file_path: str) -> ParseResult:
        try:
            result = self._parser_func(file_path)
            if isinstance(result, ParseResult):
                return result

            items = result.get("items", []) if isinstance(result, dict) else []
            return ParseResult(
                items=items,
                doc_type=self._doc_type,
                metadata=result.get("metadata", {}) if isinstance(result, dict) else {},
                parse_errors=result.get("errors", []) if isinstance(result, dict) else [],
            )
        except Exception as e:
            return ParseResult(
                items=[],
                doc_type=self._doc_type,
                metadata={},
                parse_errors=[{"error": str(e)}],
            )

    def _can_parse_impl(self, file_path: str, content_type: Optional[str]) -> bool:
        return True


class ExcelParserAdapter(BaseParserAdapter):
    def _can_parse_impl(self, file_path: str, content_type: Optional[str] = None) -> bool:
        return file_path.lower().endswith((".xlsx", ".xls", ".xlsm"))


class CSVParserAdapter(BaseParserAdapter):
    def _can_parse_impl(self, file_path: str, content_type: Optional[str] = None) -> bool:
        return file_path.lower().endswith(".csv")


class XMLParserAdapter(BaseParserAdapter):
    def _can_parse_impl(self, file_path: str, content_type: Optional[str] = None) -> bool:
        return file_path.lower().endswith(".xml")


class PDFParserAdapter(BaseParserAdapter):
    def _can_parse_impl(self, file_path: str, content_type: Optional[str] = None) -> bool:
        if file_path.lower().endswith(".pdf"):
            return True
        if content_type and "pdf" in content_type.lower():
            return True
        return False


class ImageParserAdapter(BaseParserAdapter):
    def _can_parse_impl(self, file_path: str, content_type: Optional[str] = None) -> bool:
        extensions = (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".heic", ".heif")
        return file_path.lower().endswith(extensions)
