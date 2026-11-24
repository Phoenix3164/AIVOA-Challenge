from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(60), default="Investigator")


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_no: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New RCA Investigation")
    status: Mapped[str] = mapped_column(String(60), default="Draft")
    severity: Mapped[str] = mapped_column(String(30), default="Pending")
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_quantity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufacturing_stage: Mapped[str | None] = mapped_column(String(160), nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(String(80), nullable=True)
    department: Mapped[str | None] = mapped_column(String(160), nullable=True)
    incident_category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    equipment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deviation_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deviation_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    containment_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    actual_parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_assessment: Mapped[dict] = mapped_column(JSON, default=dict)
    field_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    root_causes: Mapped[list["RootCause"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    capa_actions: Mapped[list["CapaAction"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    five_whys: Mapped[list["FiveWhy"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    fishbone_analyses: Mapped[list["FishboneAnalysis"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    evidence_gaps: Mapped[list["InvestigationGap"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    uploaded_documents: Mapped[list["UploadedDocument"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")


class DeviationDetail(Base, TimestampMixin):
    __tablename__ = "deviation_details"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    assessment: Mapped[dict] = mapped_column(JSON, default=dict)


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(60), default="Document")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="user")
    investigation: Mapped["Investigation"] = relationship(back_populates="evidence")


class RootCause(Base, TimestampMixin):
    __tablename__ = "root_causes"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    category: Mapped[str] = mapped_column(String(60), default="Machine")
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(40), default="Hypothesis")
    supporting_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    contradictory_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    investigation: Mapped["Investigation"] = relationship(back_populates="root_causes")


class ContributingFactor(Base, TimestampMixin):
    __tablename__ = "contributing_factors"
    id: Mapped[int] = mapped_column(primary_key=True)
    root_cause_id: Mapped[int] = mapped_column(ForeignKey("root_causes.id"))
    description: Mapped[str] = mapped_column(Text)


class FiveWhy(Base, TimestampMixin):
    __tablename__ = "five_whys"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    sequence: Mapped[dict] = mapped_column(JSON, default=dict)
    investigation: Mapped["Investigation"] = relationship(back_populates="five_whys")


class FishboneAnalysis(Base, TimestampMixin):
    __tablename__ = "fishbone_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    investigation: Mapped["Investigation"] = relationship(back_populates="fishbone_analyses")


class InvestigationGap(Base, TimestampMixin):
    __tablename__ = "investigation_gaps"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    investigation: Mapped["Investigation"] = relationship(back_populates="evidence_gaps")


class CapaAction(Base, TimestampMixin):
    __tablename__ = "capa_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    action_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default="Medium")
    responsible_department: Mapped[str] = mapped_column(String(120), default="Engineering")
    suggested_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    effectiveness_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Open")
    investigation: Mapped["Investigation"] = relationship(back_populates="capa_actions")


class CapaEffectiveness(Base, TimestampMixin):
    __tablename__ = "capa_effectiveness"
    id: Mapped[int] = mapped_column(primary_key=True)
    capa_action_id: Mapped[int] = mapped_column(ForeignKey("capa_actions.id"))
    criteria: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)


class CopilotMessage(Base, TimestampMixin):
    __tablename__ = "copilot_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class UploadedDocument(Base, TimestampMixin):
    __tablename__ = "uploaded_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    investigation: Mapped["Investigation"] = relationship(back_populates="uploaded_documents")


class AIAnalysisRun(Base, TimestampMixin):
    __tablename__ = "ai_analysis_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True)
    intent: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    output_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    actor: Mapped[str] = mapped_column(String(120), default="system")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
