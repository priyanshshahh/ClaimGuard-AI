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
