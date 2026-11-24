from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class RiskSchema(BaseModel):
    level: Literal["Low", "Medium", "High", "Critical", "Pending"] = "Pending"
    rationale: str = "Risk assessment pending human review."
    patient_impact: str = "Not assessed"
    product_impact: str = "Not assessed"
    recommendation: str = "Maintain containment until assessment is approved."


class InvestigationFields(BaseModel):
    title: str | None = None
    product_name: str | None = None
    api_grade: str | None = None
    batch_number: str | None = None
    affected_quantity: str | None = None
    manufacturing_stage: str | None = None
    manufacturing_date: str | None = None
    department: str | None = None
    incident_category: str | None = None
    equipment_id: str | None = None
    deviation_date: str | None = None
    deviation_description: str | None = None
    containment_actions: str | None = None
    batch_disposition: str | None = None
    expected_parameters: dict[str, str] = Field(default_factory=dict)
    actual_parameters: dict[str, str] = Field(default_factory=dict)


class EvidenceInput(BaseModel):
    name: str
    type: str = "Document"
    description: str | None = None


class InvestigationCreate(InvestigationFields):
    status: str = "Draft"


class InvestigationPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    severity: str | None = None
    product_name: str | None = None
    api_grade: str | None = None
    batch_number: str | None = None
    affected_quantity: str | None = None
    manufacturing_stage: str | None = None
    manufacturing_date: str | None = None
    department: str | None = None
    incident_category: str | None = None
    equipment_id: str | None = None
    deviation_date: str | None = None
    deviation_description: str | None = None
    containment_actions: str | None = None
    batch_disposition: str | None = None
    expected_parameters: dict[str, str] | None = None
    actual_parameters: dict[str, str] | None = None
    risk_assessment: RiskSchema | None = None


class InvestigationOut(InvestigationFields):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_no: str
    status: str
    severity: str
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    field_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    root_causes: list[dict[str, Any]] = Field(default_factory=list)
    capa_actions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_gaps: list[dict[str, Any]] = Field(default_factory=list)
    five_whys: list[dict[str, Any]] = Field(default_factory=list)
    fishbone: dict[str, Any] = Field(default_factory=dict)
    documents: list[dict[str, Any]] = Field(default_factory=list)


class CopilotRequest(BaseModel):
    message: str = Field(min_length=1, max_length=15000)
    investigation_id: int | None = None


class CopilotResponse(BaseModel):
    intent: str
    message: str
    fields: dict[str, Any] = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    evidence_gaps: list[dict[str, str]] = Field(default_factory=list)
    root_causes: list[dict[str, Any]] = Field(default_factory=list)
    five_whys: list[dict[str, str]] = Field(default_factory=list)
    fishbone: dict[str, list[str]] = Field(default_factory=dict)
    capas: list[dict[str, Any]] = Field(default_factory=list)
    demo_mode: bool
    investigation: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    analysis_type: Literal["rca", "gaps", "capa"] = "rca"


class CapaPatch(BaseModel):
    action_type: str | None = None
    description: str | None = None
    priority: str | None = None
    responsible_department: str | None = None
    suggested_owner: str | None = None
    target_date: str | None = None
    justification: str | None = None
    effectiveness_criteria: str | None = None
    status: str | None = None


class CapaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    action_type: str
    description: str
    priority: str
    responsible_department: str
    suggested_owner: str | None = None
    target_date: str | None = None
    justification: str | None = None
    effectiveness_criteria: str | None = None
    status: str
