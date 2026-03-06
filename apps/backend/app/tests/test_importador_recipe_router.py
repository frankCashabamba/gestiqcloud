import pytest

from app.modules.importador.analysis_normalizer import _normalize_analysis_output


@pytest.mark.no_db
def test_normalize_analysis_output_accepts_canonical_english_keys():
    result = _normalize_analysis_output(
        {
            "doc_type": "costing",
            "confidence": 0.91,
            "reasoning": "Detected costing worksheet",
            "fields": {"vendor": "PAN KUSI"},
        }
    )

    assert result == {
        "doc_type": "COSTING",
        "confidence": 0.91,
        "reasoning": "Detected costing worksheet",
        "fields": {"vendor": "PAN KUSI"},
    }


@pytest.mark.no_db
def test_normalize_analysis_output_accepts_legacy_spanish_keys():
    result = _normalize_analysis_output(
        {
            "tipo_documento": "receta",
            "confianza": "0.77",
            "razonamiento": "Documento de costeo",
            "campos": {"nombre_receta": "PAN KUSI"},
        }
    )

    assert result == {
        "doc_type": "RECETA",
        "confidence": 0.77,
        "reasoning": "Documento de costeo",
        "fields": {"nombre_receta": "PAN KUSI"},
    }


@pytest.mark.no_db
def test_normalize_analysis_output_falls_back_for_missing_or_invalid_values():
    result = _normalize_analysis_output(
        {
            "doc_type": "",
            "confidence": "invalid",
            "fields": ["not", "a", "dict"],
        }
    )

    assert result == {
        "doc_type": "OTHER",
        "confidence": 0.0,
        "reasoning": "",
        "fields": {},
    }
