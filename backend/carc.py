"""Derived crosswalk from ClaimGuard's agent findings / CMS CERT improper-payment
categories to the closest standard X12 CARC + CMS RARC denial reason codes.

This is a DERIVED MAPPING, not a payer remittance. The CMS CERT public file
records improper-payment *review* outcomes (No/Insufficient Documentation,
Medical Necessity, Incorrect Coding, ...), not 835/EDI CARC/RARC codes, so no
1:1 source mapping exists. The table below is a best-effort crosswalk from each
CERT error category (and the agent's documentation findings) to the CARC/RARC a
payer would most plausibly cite, so the UI can speak the industry's denial-code
language. Every row is labeled as derived in the UI.

Group codes (X12): CO=Contractual Obligation, PR=Patient Responsibility,
PI=Payer Initiated, OA=Other Adjustment. Denials in these CERT categories are
provider write-offs, hence group CO. Code definitions are from the public X12
CARC and CMS RARC code lists.
"""

from typing import Any, Dict, List

# Agent-finding key -> derived CARC/RARC mapping.
CARC_MAP: Dict[str, Dict[str, str]] = {
    "documentation_incomplete": {
        "cert_category": "Insufficient / No Documentation",
        "carc_code": "16",
        "carc_desc": "Claim/service lacks information or has submission/billing error(s).",
        "rarc_code": "N706",
        "rarc_desc": "Missing documentation.",
        "group_code": "CO",
        "group_desc": "Contractual Obligation",
    },
    "no_medical_necessity": {
        "cert_category": "Medical Necessity",
        "carc_code": "50",
        "carc_desc": "Non-covered service: not deemed a medical necessity by the payer.",
        "rarc_code": "N115",
        "rarc_desc": "Decision based on a Local Coverage Determination (LCD).",
        "group_code": "CO",
        "group_desc": "Contractual Obligation",
    },
    "procedure_mismatch": {
        "cert_category": "Incorrect Coding",
        "carc_code": "11",
        "carc_desc": "The diagnosis is inconsistent with the procedure.",
        "rarc_code": "N657",
        "rarc_desc": "This should be billed with the appropriate code for these services.",
        "group_code": "CO",
        "group_desc": "Contractual Obligation",
    },
}

# Ordered by how ClaimGuard prioritizes the *primary* reason when several apply:
# missing documentation is the single largest CERT improper-payment driver, then
# medical necessity, then coding mismatch.
_PRIORITY = ["documentation_incomplete", "no_medical_necessity", "procedure_mismatch"]


def map_findings_to_carc(
    documentation_complete: int = 1,
    clinical_justification_present: int = 1,
    procedure_mismatch_flag: int = 0,
) -> List[Dict[str, str]]:
    """Return applicable derived CARC/RARC mappings, most-likely primary first.

    Empty list means the agent found no documentation problem (no denial reason
    predicted from the findings).
    """
    applicable = {
        "documentation_incomplete": documentation_complete == 0,
        "no_medical_necessity": clinical_justification_present == 0,
        "procedure_mismatch": procedure_mismatch_flag == 1,
    }
    return [dict(CARC_MAP[key]) for key in _PRIORITY if applicable[key]]


def attach_carc(claim: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a claim dict in place with derived CARC fields, read from the
    agent flags already on the claim. Deterministic, so it is computed on read
    instead of persisted."""
    reasons = map_findings_to_carc(
        documentation_complete=int(claim.get("documentation_complete", 1) or 0),
        clinical_justification_present=int(
            claim.get("clinical_justification_present", 1) or 0
        ),
        procedure_mismatch_flag=int(claim.get("procedure_mismatch_flag", 0) or 0),
    )
    primary = reasons[0] if reasons else None
    claim["carc_reasons"] = reasons
    claim["carc_code"] = primary["carc_code"] if primary else None
    claim["carc_group"] = primary["group_code"] if primary else None
    claim["cert_category"] = primary["cert_category"] if primary else None
    return claim
