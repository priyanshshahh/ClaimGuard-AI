import json
import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator

from deidentify import scrub_phi

load_dotenv()

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "google/gemma-3-27b-it")

# Hard timeout (seconds) for every LLM HTTP call so a hung provider connection
# is bounded instead of wedging the request. Overridable via LLM_TIMEOUT.
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "20"))

MEDICAL_RULES_PROMPT = """
Evaluate the clinical note against billed ICD-10 and CPT codes using these denial rules:

CO-11 (Diagnosis Inconsistent with Procedure):
- Verify ICD-10 logically supports the CPT procedure.
- Example: CPT 93000 (ECG) requires cardiovascular symptoms/diagnosis in the note.

CO-16 (Missing Information):
- Flag incomplete demographics, missing physician signature, or absent required fields.

CPT 99214 (Level 4 E/M):
- Verify moderate complexity OR explicit documentation of 30-39 total minutes of care.

CO-50 (Medical Necessity): Flag absent clinical justification.
CO-97 (Level mismatch): Flag when E/M level exceeds documented complexity.

Return predicted_denial_codes as an array (e.g. ["CO-11", "CO-16"]) or [].
"""


class ClinicalAnalysis(BaseModel):
    # strict=True guards against schema drift, but real LLM output uses JSON
    # booleans for the 0/1 flags, null for optional strings, and bare ints
    # for confidence - coerce those specific shapes instead of silently
    # falling back (bug found in a live Groq verification run).
    model_config = ConfigDict(extra="forbid", strict=True)

    documentation_complete: int = Field(description="1 if complete, 0 if missing critical elements")
    clinical_justification_present: int = Field(description="1 if medical necessity documented, 0 otherwise")
    procedure_mismatch_flag: int = Field(description="1 if CPT/ICD mismatch, 0 otherwise")
    agent_correction_draft: str = Field(description="Ready-to-paste clinical justification")
    explanation: str = Field(description="Clear explanation of denial risk")
    confidence: float = Field(ge=0.0, le=1.0, default=0.82)
    missing_elements: List[str] = Field(default_factory=list)
    predicted_denial_codes: List[str] = Field(default_factory=list)

    @field_validator(
        "documentation_complete",
        "clinical_justification_present",
        "procedure_mismatch_flag",
        mode="before",
    )
    @classmethod
    def _bool_to_int(cls, v):
        return int(v) if isinstance(v, bool) else v

    @field_validator("agent_correction_draft", "explanation", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return "" if v is None else v

    @field_validator("confidence", mode="before")
    @classmethod
    def _int_confidence(cls, v):
        return float(v) if isinstance(v, int) and not isinstance(v, bool) else v


class AppealLetter(BaseModel):
    subject: str
    body: str
    recommended_attachments: List[str] = Field(default_factory=list)


class PolicyCheckResult(BaseModel):
    payer: str
    policy_reference: str
    compliance_status: str
    risk_summary: str
    required_documentation: List[str] = Field(default_factory=list)


def _nebius_client() -> Optional[OpenAI]:
    key = os.getenv("NEBIUS_API_KEY")
    if not key:
        return None
    return OpenAI(base_url=NEBIUS_BASE_URL, api_key=key, timeout=LLM_TIMEOUT)


def _groq_llm(temperature: float = 0.18):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("No LLM API key configured")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        max_tokens=1700,
        api_key=api_key,
        timeout=LLM_TIMEOUT,
        max_retries=1,
    )


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _nebius_chat(system: str, user: str, temperature: float = 0.15) -> str:
    client = _nebius_client()
    if not client:
        raise ValueError("NEBIUS_API_KEY not configured")
    response = client.chat.completions.create(
        model=NEBIUS_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


def _call_llm(system: str, user: str, model_cls, fallback: dict, temperature: float = 0.2) -> dict:
    """Single LLM path for every task: try Nebius (strict JSON) first, then
    Groq, validating the response against ``model_cls``. Returns the documented
    ``fallback`` dict if both providers are unset or fail. Replaces the six
    near-identical provider call sites that used to live in this module.
    """
    if _nebius_client():
        try:
            raw = _nebius_chat(system, user, temperature)
            return model_cls.model_validate(_extract_json(raw)).model_dump()
        except Exception:
            pass
    if os.getenv("GROQ_API_KEY"):
        try:
            resp = _groq_llm(temperature).invoke(
                [SystemMessage(content=system), HumanMessage(content=user)]
            )
            return model_cls.model_validate(_extract_json(resp.content)).model_dump()
        except Exception:
            pass
    return dict(fallback)


def _fallback_clinical() -> dict:
    return {
        "documentation_complete": 0,
        "clinical_justification_present": 0,
        "procedure_mismatch_flag": 0,
        "agent_correction_draft": (
            "Additional documentation of medical necessity and prior treatment failure is recommended."
        ),
        "explanation": "Automated analysis limited. Manual compliance review advised.",
        "confidence": 0.6,
        "missing_elements": ["Failed conservative management documentation", "Explicit medical necessity statement"],
        "predicted_denial_codes": ["CO-16"],
    }


def analyze_clinical_notes(notes: str, icd_code: str, cpt_code: str) -> dict:
    # De-identify before any third-party LLM call (see deidentify.py limitations).
    notes = scrub_phi(notes)
    schema_hint = json.dumps(ClinicalAnalysis.model_json_schema())
    system = (
        "You are an elite medical billing compliance specialist. "
        "Return ONLY valid JSON matching this schema exactly:\n"
        f"{schema_hint}\n\n{MEDICAL_RULES_PROMPT}"
    )
    user = f"Notes: {notes}\nICD-10: {icd_code}\nCPT: {cpt_code}\n\nAnalyze denial risk."
    return _call_llm(system, user, ClinicalAnalysis, _fallback_clinical(), 0.15)


def generate_appeal_letter(
    claim_data: Dict, original_analysis: Dict, denial_reason: str = "Medical necessity"
) -> dict:
    system = (
        "You are a healthcare appeals attorney. Return ONLY JSON with keys: "
        "subject, body, recommended_attachments (array). Ground the appeal in the "
        "clinical note: quote the exact supporting passage(s) verbatim in the body, "
        "and explicitly name and rebut the denial reason code you were given."
    )
    note_excerpt = scrub_phi(claim_data.get("patient_chart_notes", ""))[:900]
    user = (
        f"Claim: {claim_data.get('claim_id')} | Payer: {claim_data.get('payer_id')} | "
        f"${claim_data.get('claim_value_usd')}\nICD: {claim_data.get('icd_10_code')} "
        f"CPT: {claim_data.get('cpt_code')}\nClinical note (quote from this verbatim): "
        f"{note_excerpt}\n"
        f"Risk: {original_analysis.get('explanation', '')}\n"
        f"Denial reason / CARC to rebut: {denial_reason}"
    )
    fallback = {
        "subject": f"Request for Reconsideration - Claim {claim_data.get('claim_id')}",
        "body": (
            "We respectfully request reconsideration based on documented medical "
            f"necessity, rebutting {denial_reason}. Supporting note excerpt: "
            f"\"{note_excerpt[:300]}\""
        ),
        "recommended_attachments": ["Clinical notes", "Imaging", "Physician attestation"],
    }
    return _call_llm(system, user, AppealLetter, fallback, 0.22)


def check_payer_policy(notes: str, icd_code: str, cpt_code: str, payer_id: str) -> dict:
    system = (
        "You are a payer policy expert. Return JSON: payer, policy_reference, "
        "compliance_status (COMPLIANT/NON_COMPLIANT/NEEDS_CLARIFICATION), "
        "risk_summary, required_documentation (array)."
    )
    user = f"Payer: {payer_id}\nICD: {icd_code} CPT: {cpt_code}\nNotes: {scrub_phi(notes)[:700]}"
    fallback = {
        "payer": payer_id,
        "policy_reference": f"{payer_id} Medical Necessity Guidelines",
        "compliance_status": "NEEDS_CLARIFICATION",
        "risk_summary": "Additional documentation recommended.",
        "required_documentation": ["Visit time documentation", "Medical necessity statement"],
    }
    return _call_llm(system, user, PolicyCheckResult, fallback, 0.1)
