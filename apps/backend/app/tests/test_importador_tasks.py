from __future__ import annotations

import pytest

from app.modules.importador.tasks import _should_run_inline_ai


@pytest.mark.no_db
def test_should_run_inline_ai_skips_visual_uploads():
    assert (
        _should_run_inline_ai(
            tipo_archivo="JPG",
            estado="REVIEW",
            doc_tipo="OTHER",
        )
        is False
    )


@pytest.mark.no_db
def test_should_run_inline_ai_keeps_non_visual_uncertain_docs():
    assert (
        _should_run_inline_ai(
            tipo_archivo="PDF",
            estado="REVIEW",
            doc_tipo="OTHER",
        )
        is True
    )
