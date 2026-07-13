"""Tests for the PHI scrubber applied before third-party LLM calls."""

from deidentify import contains_probable_phi, scrub_phi


def test_scrubs_ssn():
    out = scrub_phi("SSN 123-45-6789 on file.")
    assert "123-45-6789" not in out
    assert "[REDACTED-SSN]" in out


def test_scrubs_phone_numbers():
    out = scrub_phi("Call the patient at (617) 555-0182 or 617-555-0182.")
    assert "555-0182" not in out
    assert out.count("[REDACTED-PHONE]") == 2


def test_scrubs_email():
    out = scrub_phi("Contact jane.doe+chart@example.org for records.")
    assert "example.org" not in out
    assert "[REDACTED-EMAIL]" in out


def test_scrubs_mrn_and_member_ids():
    out = scrub_phi("MRN: 88421739. Member ID A1B2C3D4 active.")
    assert "88421739" not in out
    assert "A1B2C3D4" not in out


def test_scrubs_dob_and_dates():
    out = scrub_phi("DOB: 01/02/1958. Seen on 03/04/2026 and again May 5, 2026.")
    assert "1958" not in out
    assert "03/04/2026" not in out
    assert "May 5, 2026" not in out


def test_scrubs_titled_and_labeled_names():
    out = scrub_phi("Patient: John Smith seen by Dr. Alice Wong.")
    assert "John Smith" not in out
    assert "Alice Wong" not in out


def test_scrubs_street_address():
    out = scrub_phi("Lives at 42 Beacon Street, unit 3, 02108-1234.")
    assert "Beacon" not in out
    assert "02108-1234" not in out


def test_preserves_clinical_content():
    note = (
        "67 y/o F with end-stage OA right knee. Failed 9 months conservative care "
        "including PT and NSAIDs. Pain 8/10. TKA indicated."
    )
    assert scrub_phi(note) == note


def test_contains_probable_phi_flag():
    assert contains_probable_phi("SSN 123-45-6789")
    assert not contains_probable_phi("Severe medial joint space narrowing.")


def test_empty_and_none_safe():
    assert scrub_phi("") == ""
    assert scrub_phi(None) is None
