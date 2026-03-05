from __future__ import annotations

import re

from .schema import TemplateV2


class TemplateMatcher:
    def __init__(self, templates: list[TemplateV2]):
        self.templates = templates

    def match(self, filename: str, language: str = "es") -> TemplateV2 | None:
        candidates: list[TemplateV2] = []
        for tpl in self.templates:
            if tpl.match.filename_regex:
                try:
                    if not re.search(tpl.match.filename_regex, filename, re.IGNORECASE):
                        continue
                except re.error:
                    continue
            if language not in tpl.match.language:
                continue
            candidates.append(tpl)

        if not candidates:
            return None

        candidates.sort(key=lambda t: t.match.priority, reverse=True)
        return candidates[0]
