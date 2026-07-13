"""Unit tests for strict Pydantic agent extraction schema."""

import pytest
from pydantic import ValidationError

from agent import ClinicalAnalysis


def test_strict_schema_accepts_valid_payload():
    result = ClinicalAnalysis.model_validate(
        {
            "documentation_complete": 0,
            "clinical_justification_present": 0,
            "procedure_mismatch_flag": 1,
            "agent_correction_draft": "Documentation supports medical necessity.",
            "explanation": "CPT/ICD mismatch detected.",
            "confidence": 0.88,
            "missing_elements": ["Time documentation"],
            "predicted_denial_codes": ["CO-11"],
        }
    )
    assert result.documentation_complete == 0
    assert result.procedure_mismatch_flag == 1
    assert "CO-11" in result.predicted_denial_codes


def test_strict_schema_rejects_extra_keys():
    with pytest.raises(ValidationError):
        ClinicalAnalysis.model_validate(
            {
                "documentation_complete": 1,
                "clinical_justification_present": 1,
                "procedure_mismatch_flag": 0,
                "agent_correction_draft": "OK",
                "explanation": "OK",
                "confidence": 0.9,
                "missing_elements": [],
                "predicted_denial_codes": [],
                "hallucinated_key": True,
            }
        )


def test_strict_schema_rejects_wrong_types():
    with pytest.raises(ValidationError):
        ClinicalAnalysis.model_validate(
            {
                "documentation_complete": "yes",
                "clinical_justification_present": 1,
                "procedure_mismatch_flag": 0,
                "agent_correction_draft": "OK",
                "explanation": "OK",
                "confidence": 0.9,
                "missing_elements": [],
                "predicted_denial_codes": [],
            }
        )


def test_llm_json_booleans_coerced_to_int_flags():
    """Regression: live Groq output uses JSON booleans for the 0/1 flags and
    null for optional strings; strict mode used to reject the whole payload
    and silently fall back to the canned response."""
    result = ClinicalAnalysis.model_validate(
        {
            "documentation_complete": True,
            "clinical_justification_present": False,
            "procedure_mismatch_flag": False,
            "agent_correction_draft": None,
            "explanation": "Necessity not documented.",
            "confidence": 1,
            "missing_elements": [],
            "predicted_denial_codes": ["CO-50"],
        }
    )
    assert result.documentation_complete == 1
    assert result.clinical_justification_present == 0
    assert result.agent_correction_draft == ""
    assert result.confidence == 1.0


def test_scrub_applied_before_llm(monkeypatch):
    """analyze_clinical_notes must pass de-identified notes to the LLM path."""
    import agent as agent_mod

    captured = {}

    def fake_langchain(notes, icd, cpt):
        captured["notes"] = notes
        return {"documentation_complete": 1}

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(agent_mod, "_nebius_client", lambda: None)
    monkeypatch.setattr(agent_mod, "_parse_clinical_langchain", fake_langchain)
    agent_mod.analyze_clinical_notes(
        notes="Patient: John Smith, DOB: 01/02/1958, MRN: 445566. Chest pain.",
        icd_code="I25.10",
        cpt_code="93458",
    )
    assert "John Smith" not in captured["notes"]
    assert "01/02/1958" not in captured["notes"]
    assert "445566" not in captured["notes"]
    assert "Chest pain" in captured["notes"]
