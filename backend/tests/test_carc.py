"""Tests for the derived CARC/RARC mapping."""

from carc import attach_carc, map_findings_to_carc


def test_clean_claim_has_no_denial_reason():
    assert map_findings_to_carc(1, 1, 0) == []


def test_missing_documentation_maps_to_carc_16():
    reasons = map_findings_to_carc(documentation_complete=0)
    assert reasons[0]["carc_code"] == "16"
    assert reasons[0]["group_code"] == "CO"
    assert reasons[0]["rarc_code"] == "N706"


def test_medical_necessity_maps_to_carc_50():
    reasons = map_findings_to_carc(clinical_justification_present=0)
    assert reasons[0]["carc_code"] == "50"


def test_procedure_mismatch_maps_to_carc_11():
    reasons = map_findings_to_carc(procedure_mismatch_flag=1)
    assert reasons[0]["carc_code"] == "11"


def test_primary_reason_priority_documentation_first():
    # all three problems present -> documentation is the primary (first) reason
    reasons = map_findings_to_carc(0, 0, 1)
    assert [r["carc_code"] for r in reasons] == ["16", "50", "11"]


def test_attach_carc_sets_fields_from_flags():
    claim = {"documentation_complete": 0, "clinical_justification_present": 1,
             "procedure_mismatch_flag": 0}
    attach_carc(claim)
    assert claim["carc_code"] == "16"
    assert claim["carc_group"] == "CO"
    assert claim["cert_category"].startswith("Insufficient")
    assert len(claim["carc_reasons"]) == 1


def test_attach_carc_clean_claim_is_none():
    claim = {"documentation_complete": 1, "clinical_justification_present": 1,
             "procedure_mismatch_flag": 0}
    attach_carc(claim)
    assert claim["carc_code"] is None
    assert claim["carc_reasons"] == []
