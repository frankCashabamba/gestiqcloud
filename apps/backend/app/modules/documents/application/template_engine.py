from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.modules.documents.domain.models import DocumentModel


class TemplateEngine:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[3]  # apps/backend/app
        self.templates_dir = base_dir / "templates" / "documents"
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, doc: DocumentModel) -> str:
        template_path = self._select_template(doc)
        template = self.env.get_template(template_path)
        data = doc.model_dump()
        html = template.render(**data)
        if not html.endswith("\n"):
            html += "\n"
        return html

    def _select_template(self, doc: DocumentModel) -> str:
        doc_type = doc.document.type.lower()
        doc_type = "ticket_no_fiscal" if doc_type == "ticket_no_fiscal" else doc_type
        fmt = doc.render.format.lower()
        version = int(doc.render.templateVersion)

        tenant_id = doc.seller.tenantId
        tenant_path = (
            f"tenants/{tenant_id}/{doc_type}.{fmt}.v{version}.html"
        )
        default_path = f"default/{doc_type}/{fmt}.v{version}.html"

        if (self.templates_dir / tenant_path).exists():
            return tenant_path
        return default_path
