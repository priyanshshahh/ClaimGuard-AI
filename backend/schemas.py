from pydantic import BaseModel, Field
from typing import List, Optional


class PolicyCheckRequest(BaseModel):
    claim_id: Optional[str] = None
    icd: Optional[str] = None
    cpt: Optional[str] = None
    payer: Optional[str] = None
    notes: Optional[str] = None


class ClaimInput(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier")
    claim_value_usd: float = Field(..., gt=0, description="Total billed amount in USD")
    payer_id: str = Field(..., description="Insurance payer identifier")
    icd_10_code: str = Field(..., description="ICD-10 diagnosis code")
    cpt_code: str = Field(..., description="CPT procedure code")
    patient_chart_notes: str = Field(..., min_length=50, description="Unstructured clinical notes")


class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    claim_value_usd: float = 0.0
    denial_probability: float
    risk_level: str
    expected_loss_usd: float
    documentation_complete: int
    clinical_justification_present: int = 1
    procedure_mismatch_flag: int = 0
    procedure_mismatch: int = 0  # backward compat alias
    agent_correction_draft: str
    explanation: str
    recommended_action: str
    confidence: float = 0.82
    missing_elements: list = []
    predicted_denial_codes: List[str] = []
    payer_days_to_pay: int = 35
    cash_flow_urgency: float = 0.0
    knapsack_selected: Optional[bool] = None
    # calibrated model output before the documented heuristic uplift
    model_base_probability: Optional[float] = None
    is_demo: bool = False
