"""Best-effort de-identification of clinical notes before third-party LLM calls.

Scrubs obvious PHI with regex/heuristic passes:
  - SSNs, phone numbers, email addresses
  - MRN / member / account / policy identifiers
  - dates of birth and explicit full dates
  - names introduced by titles (Dr./Mr./Mrs./Ms.) or "Patient(name):" labels
  - street addresses and ZIP codes

LIMITATION (documented, on purpose): this is a demo system, not a certified
HIPAA de-identification pipeline. Regexes cannot catch free-text names with
no cue words, rare identifiers, or contextual re-identification. Do not send
real patient data through this service.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern, str]] = [
    # SSN: 123-45-6789 or 123 45 6789
    (re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b"), "[REDACTED-SSN]"),
    # US phone numbers: (555) 123-4567, 555-123-4567, +1 555 123 4567
    (
        re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
        "[REDACTED-PHONE]",
    ),
    # email
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[REDACTED-EMAIL]"),
    # MRN / member / account / policy / chart identifiers
    (
        re.compile(
            r"\b(?:MRN|medical record(?: number)?|member(?: id)?|account(?: no| number)?|"
            r"policy(?: no| number)?|chart(?: no| number)?)\s*[:#]?\s*[A-Za-z0-9-]{4,}\b",
            re.IGNORECASE,
        ),
        "[REDACTED-MRN]",
    ),
    # DOB with explicit label, any date format after it
    (
        re.compile(
            r"\b(?:DOB|date of birth|born(?: on)?)\s*[:#]?\s*[A-Za-z0-9,/\-\. ]{6,20}\b",
            re.IGNORECASE,
        ),
        "[REDACTED-DOB]",
    ),
    # bare full dates: 01/02/1965, 1965-02-01, Jan 2, 1965
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), "[REDACTED-DATE]"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "[REDACTED-DATE]"),
    (
        re.compile(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
            r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+"
            r"\d{1,2},?\s+\d{4}\b",
            re.IGNORECASE,
        ),
        "[REDACTED-DATE]",
    ),
    # names cued by a label: "Patient: John Smith", "Patient name John Smith"
    (
        re.compile(
            r"\b(?:patient(?:\s+name)?|name)\s*[:#]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}",
            re.IGNORECASE,
        ),
        "Patient: [REDACTED-NAME]",
    ),
    # names cued by titles: Dr. Jane Doe, Mr Smith
    (
        re.compile(
            r"\b(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
        ),
        "[REDACTED-NAME]",
    ),
    # street addresses: 123 Main St / Ave / Rd / Blvd ...
    (
        re.compile(
            r"\b\d{1,5}\s+[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)?\s+"
            r"(?:St(?:reet)?|Ave(?:nue)?|R(?:oa)?d|Blvd|Boulevard|Ln|Lane|Dr(?:ive)?|Ct|Court|Way)\b\.?",
        ),
        "[REDACTED-ADDRESS]",
    ),
    # ZIP+4 or bare 5-digit ZIP right after a state-ish token
    (re.compile(r"\b\d{5}-\d{4}\b"), "[REDACTED-ZIP]"),
]


def scrub_phi(text: str) -> str:
    """Return `text` with obvious PHI replaced by [REDACTED-*] tokens."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def contains_probable_phi(text: str) -> bool:
    """True if any scrub pattern still matches (useful for tests/monitoring)."""
    return any(p.search(text or "") for p, _ in _PATTERNS)
