from __future__ import annotations
from datetime import datetime
import fitz
from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload
from .ai_graph import run_analysis
from .config import get_settings
from .database import Base, engine, ensure_investigation_columns, get_db
from .models import AIAnalysisRun, ActivityLog, CapaAction, CopilotMessage, Evidence, FishboneAnalysis, FiveWhy, Investigation, InvestigationGap, RootCause, UploadedDocument, User
from .reports import build_investigation_report
from .schemas import AnalysisRequest, CapaOut, CapaPatch, CopilotRequest, CopilotResponse, EvidenceInput, InvestigationCreate, InvestigationOut, InvestigationPatch, LoginRequest, TokenResponse

settings = get_settings()
app = FastAPI(title="PharmaRCA AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_investigation_columns()
    with next(get_db()) as db:
        if not db.query(User).filter_by(email="qa@pharmarca.local").first():
            db.add(User(email="qa@pharmarca.local", full_name="QA Reviewer", password_hash="demo123", role="QA Reviewer"))
            db.commit()


def serialize(inv: Investigation) -> dict:
    latest_five_whys = inv.five_whys[-1].sequence.get("items", []) if inv.five_whys else []
    latest_fishbone = inv.fishbone_analyses[-1].analysis if inv.fishbone_analyses else {}
    return {"id": inv.id, "investigation_no": inv.investigation_no, "title": inv.title, "status": inv.status, "severity": inv.severity, "product_name": inv.product_name, "api_grade": inv.api_grade, "batch_number": inv.batch_number, "affected_quantity": inv.affected_quantity, "manufacturing_stage": inv.manufacturing_stage, "manufacturing_date": inv.manufacturing_date, "department": inv.department, "incident_category": inv.incident_category, "equipment_id": inv.equipment_id, "deviation_date": inv.deviation_date, "deviation_description": inv.deviation_description, "containment_actions": inv.containment_actions, "batch_disposition": inv.batch_disposition, "expected_parameters": inv.expected_parameters or {}, "actual_parameters": inv.actual_parameters or {}, "risk_assessment": inv.risk_assessment or {}, "field_metadata": inv.field_metadata or {}, "created_at": inv.created_at, "updated_at": inv.updated_at, "evidence": [{"id": e.id, "name": e.name, "type": e.type, "description": e.description} for e in inv.evidence], "root_causes": [{"id": r.id, "category": r.category, "description": r.description, "confidence": r.confidence, "supporting_evidence": r.supporting_evidence, "contradictory_evidence": r.contradictory_evidence, "verification_requirements": r.verification_requirements, "confirmed": r.confirmed} for r in inv.root_causes], "capa_actions": [{"id": c.id, "action_type": c.action_type, "description": c.description, "priority": c.priority, "responsible_department": c.responsible_department, "suggested_owner": c.suggested_owner, "target_date": c.target_date, "justification": c.justification, "effectiveness_criteria": c.effectiveness_criteria, "status": c.status} for c in inv.capa_actions], "evidence_gaps": [{"id": gap.id, "description": gap.description, "rationale": gap.rationale} for gap in inv.evidence_gaps], "five_whys": latest_five_whys, "fishbone": latest_fishbone, "documents": [{"id": doc.id, "filename": doc.filename, "content_type": doc.content_type, "created_at": doc.created_at} for doc in inv.uploaded_documents]}


def get_investigation(db: Session, investigation_id: int) -> Investigation:
    inv = db.query(Investigation).options(selectinload(Investigation.evidence), selectinload(Investigation.root_causes), selectinload(Investigation.capa_actions), selectinload(Investigation.five_whys), selectinload(Investigation.fishbone_analyses), selectinload(Investigation.evidence_gaps), selectinload(Investigation.uploaded_documents)).filter(Investigation.id == investigation_id).first()
    if not inv: raise HTTPException(404, "Investigation not found")
    return inv


def next_no(db: Session) -> str:
    return f"RCA-{datetime.utcnow():%Y%m%d}-{db.query(Investigation).count() + 1:03d}"


def apply_fields(inv: Investigation, fields: dict, ai_generated: bool = True) -> None:
    # Copy before assignment: plain SQLAlchemy JSON columns do not detect an
    # in-place mutation, which previously made review/source metadata stale.
    metadata = dict(inv.field_metadata or {})
    # An investigator's edit is authoritative. Subsequent AI calls can still
    # suggest a value in their response, but cannot overwrite it in storage.
    safe = {k: v for k, v in fields.items() if hasattr(inv, k) and v not in (None, "", {}) and (not ai_generated or metadata.get(k, {}).get("source") != "human")}
    for key, value in safe.items(): setattr(inv, key, value)
    metadata.update({key: {"source": "ai" if ai_generated else "human", "requires_review": ai_generated, "updated_at": datetime.utcnow().isoformat()} for key in safe})
    inv.field_metadata = metadata
    update_investigation_title(inv)


def update_investigation_title(inv: Investigation) -> None:
    """Use known investigation facts only; a human-entered title remains final."""
    metadata = inv.field_metadata or {}
    if metadata.get("title", {}).get("source") == "human":
        return
    parts = [value.strip() for value in (inv.product_name, inv.batch_number, inv.incident_category) if value and value.strip()]
    if parts:
        inv.title = " | ".join(parts)
        metadata = dict(metadata)
        metadata["title"] = {"source": "system", "requires_review": True, "updated_at": datetime.utcnow().isoformat()}
        inv.field_metadata = metadata


def persist_analysis(db: Session, inv: Investigation | None, result: dict, message: str) -> None:
    inv_id = inv.id if inv else None
    db.add(AIAnalysisRun(investigation_id=inv_id, intent=result["intent"], model=settings.groq_model if settings.groq_api_key and not settings.demo_mode else "deterministic-demo", input_snapshot={"message": message}, output_snapshot=jsonable_encoder(result)))
    if inv:
        db.add(CopilotMessage(investigation_id=inv.id, role="user", content=message))
        db.add(CopilotMessage(investigation_id=inv.id, role="assistant", content=result["response"], metadata_json={"intent": result["intent"]}))
    db.commit()


@app.get("/api/health")
def health(): return {"status": "ok", "demo_mode": settings.demo_mode or not bool(settings.groq_api_key)}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user or user.password_hash != payload.password: raise HTTPException(401, "Invalid credentials")
    return {"access_token": f"demo-token-{user.id}", "user": {"id": user.id, "email": user.email, "name": user.full_name, "role": user.role}}


@app.post("/api/investigations", response_model=InvestigationOut)
def create_investigation(payload: InvestigationCreate, db: Session = Depends(get_db)):
    inv = Investigation(investigation_no=next_no(db), **payload.model_dump())
    db.add(inv); db.commit(); db.refresh(inv)
    return serialize(get_investigation(db, inv.id))


@app.get("/api/investigations", response_model=list[InvestigationOut])
def list_investigations(db: Session = Depends(get_db)):
    rows = db.query(Investigation).options(selectinload(Investigation.evidence), selectinload(Investigation.root_causes), selectinload(Investigation.capa_actions), selectinload(Investigation.five_whys), selectinload(Investigation.fishbone_analyses), selectinload(Investigation.evidence_gaps), selectinload(Investigation.uploaded_documents)).order_by(Investigation.updated_at.desc()).all()
    return [serialize(r) for r in rows]


@app.get("/api/investigations/{investigation_id}", response_model=InvestigationOut)
def read_investigation(investigation_id: int, db: Session = Depends(get_db)):
    return serialize(get_investigation(db, investigation_id))


@app.get("/api/investigations/{investigation_id}/report")
def download_investigation_report(investigation_id: int, db: Session = Depends(get_db)):
    inv = get_investigation(db, investigation_id)
    report = build_investigation_report(serialize(inv))
    filename = f"{inv.investigation_no}-RCA-report.pdf"
    return Response(content=report, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.patch("/api/investigations/{investigation_id}", response_model=InvestigationOut)
def patch_investigation(investigation_id: int, payload: InvestigationPatch, db: Session = Depends(get_db)):
    inv = get_investigation(db, investigation_id)
    apply_fields(inv, payload.model_dump(exclude_none=True), ai_generated=False)
    db.add(ActivityLog(investigation_id=inv.id, action="Investigation updated", actor="QA Reviewer")); db.commit()
    return serialize(get_investigation(db, inv.id))


@app.post("/api/investigations/{investigation_id}/evidence", response_model=InvestigationOut)
def add_evidence(investigation_id: int, payload: EvidenceInput, db: Session = Depends(get_db)):
    inv = get_investigation(db, investigation_id)
    db.add(Evidence(investigation_id=inv.id, **payload.model_dump())); db.commit()
    return serialize(get_investigation(db, inv.id))


def store_result(db: Session, inv: Investigation, result: dict) -> None:
    if result.get("fields"): apply_fields(inv, result["fields"], ai_generated=True)
    if result.get("risk_assessment"): inv.risk_assessment = result["risk_assessment"]; inv.severity = result["risk_assessment"].get("level", "Pending")
    for gap in result.get("evidence_gaps", []):
        if not db.query(InvestigationGap).filter_by(investigation_id=inv.id, description=gap["description"]).first():
            db.add(InvestigationGap(investigation_id=inv.id, description=gap["description"], rationale=gap["rationale"]))
    if result.get("five_whys") and not db.query(FiveWhy).filter_by(investigation_id=inv.id, sequence={"items": result["five_whys"]}).first():
        db.add(FiveWhy(investigation_id=inv.id, sequence={"items": result["five_whys"]}))
    if result.get("fishbone") and not db.query(FishboneAnalysis).filter_by(investigation_id=inv.id, analysis=result["fishbone"]).first():
        db.add(FishboneAnalysis(investigation_id=inv.id, analysis=result["fishbone"]))
    for root in result.get("root_causes", []):
        if not db.query(RootCause).filter_by(investigation_id=inv.id, description=root["description"]).first():
            db.add(RootCause(investigation_id=inv.id, **root))
    for action in result.get("capas", []):
        # CAPA type is the stable generated slot. Matching it preserves an
        # investigator's edited wording when analysis is re-run.
        if not db.query(CapaAction).filter_by(investigation_id=inv.id, action_type=action["action_type"]).first():
            db.add(CapaAction(investigation_id=inv.id, **action))


def response(result: dict, inv: Investigation | None = None) -> dict:
    base = {k: result.get(k, {} if k in ("fields", "risk_assessment", "fishbone") else []) for k in ["intent", "fields", "changed_fields", "risk_assessment", "evidence_gaps", "root_causes", "five_whys", "fishbone", "capas"]}
    return {**base, "message": result["response"], "demo_mode": settings.demo_mode or not bool(settings.groq_api_key), "warnings": result.get("warnings", []), "investigation": serialize(get_investigation_for_response(inv)) if inv else None}


def get_investigation_for_response(inv: Investigation) -> Investigation:
    # Relationships are already loaded for API requests; refreshing makes JSON
    # fields and timestamps reflect the transaction just committed.
    return inv


@app.post("/api/copilot/message", response_model=CopilotResponse)
def copilot_message(payload: CopilotRequest, db: Session = Depends(get_db)):
    inv = get_investigation(db, payload.investigation_id) if payload.investigation_id else None
    result = run_analysis(payload.message, {"fields": serialize(inv) if inv else {}})
    if inv: store_result(db, inv, result)
    persist_analysis(db, inv, result, payload.message)
    return response(result, inv)


@app.post("/api/copilot/upload", response_model=CopilotResponse)
async def upload_pdf(file: UploadFile = File(...), investigation_id: int = Form(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"): raise HTTPException(400, "Only PDF uploads are supported")
    try: text = "\n".join(page.get_text() for page in fitz.open(stream=await file.read(), filetype="pdf")).strip()
    except Exception as exc: raise HTTPException(400, f"Could not read PDF: {exc}")
    if not text: raise HTTPException(400, "The PDF contains no extractable text")
    inv = get_investigation(db, investigation_id)
    db.add(UploadedDocument(investigation_id=investigation_id, filename=file.filename, extracted_text=text, content_type=file.content_type))
    result = run_analysis(text, {"fields": serialize(inv), "document_text": text})
    store_result(db, inv, result)
    # A PDF with an incident result provides enough context for provisional
    # investigation outputs. They remain Pending Review, never confirmed.
    has_context = bool(result.get("fields", {}).get("incident_category") or result.get("fields", {}).get("actual_parameters") or result.get("fields", {}).get("deviation_description"))
    if has_context:
        # Document text is only the extraction trigger. Analyses use the
        # persisted context so their explicit RCA/gaps/CAPA intent wins.
        analysis_context = {"fields": serialize(inv)}
        analyses = [
            run_analysis("Run 5 Whys and Fishbone root cause analysis", analysis_context),
            run_analysis("Identify missing evidence", analysis_context),
            run_analysis("Generate CAPA recommendations", analysis_context),
        ]
        for analysis_result in analyses:
            store_result(db, inv, analysis_result)
        rca_result, gaps_result, capa_result = analyses
        result.update({"root_causes": rca_result.get("root_causes", []), "five_whys": rca_result.get("five_whys", []), "fishbone": rca_result.get("fishbone", {}), "evidence_gaps": gaps_result.get("evidence_gaps", []), "capas": capa_result.get("capas", [])})
        result["response"] = f"Extracted text from {file.filename}. Form fields, provisional RCA, evidence gaps, and CAPA recommendations are ready for review."
        for warning in [*rca_result.get("warnings", []), *gaps_result.get("warnings", []), *capa_result.get("warnings", [])]:
            result.setdefault("warnings", []).append(warning)
    else:
        result["response"] = f"Extracted text from {file.filename}. {result['response']} More incident detail is needed before RCA and CAPA suggestions can be generated."
    persist_analysis(db, inv, result, f"Document extraction: {file.filename}")
    db.refresh(inv)
    return response(result, inv)


@app.post("/api/investigations/{investigation_id}/analyze", response_model=CopilotResponse)
def analyze(investigation_id: int, payload: AnalysisRequest, db: Session = Depends(get_db)):
    inv = get_investigation(db, investigation_id)
    prompts = {"rca": "Run 5 Whys and Fishbone root cause analysis", "gaps": "Identify missing evidence", "capa": "Generate CAPA recommendations"}
    result = run_analysis(prompts[payload.analysis_type], {"fields": serialize(inv)})
    store_result(db, inv, result); persist_analysis(db, inv, result, prompts[payload.analysis_type])
    return response(result, inv)


@app.post("/api/investigations/{investigation_id}/capa/generate", response_model=CopilotResponse)
def generate_capa(investigation_id: int, db: Session = Depends(get_db)):
    return analyze(investigation_id, AnalysisRequest(analysis_type="capa"), db)


@app.patch("/api/capa/{capa_id}", response_model=CapaOut)
def patch_capa(capa_id: int, payload: CapaPatch, db: Session = Depends(get_db)):
    capa = db.query(CapaAction).filter(CapaAction.id == capa_id).first()
    if not capa: raise HTTPException(404, "CAPA recommendation not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(capa, key, value)
    db.add(ActivityLog(investigation_id=capa.investigation_id, action="CAPA recommendation updated", actor="QA Reviewer"))
    db.commit(); db.refresh(capa)
    return capa


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    rows = db.query(Investigation).all(); capas = db.query(CapaAction).all()
    statuses = ["Draft", "Under Investigation", "Pending QA Review", "RCA Approved", "CAPA In Progress", "Effectiveness Verification", "Closed"]
    severity = ["Critical", "High", "Medium", "Low", "Pending"]
    return {"total": len(rows), "open": sum(r.status not in ("Closed", "RCA Approved") for r in rows), "pending_qa": sum(r.status == "Pending QA Review" for r in rows), "approved": sum(r.status == "RCA Approved" for r in rows), "capas_in_progress": sum(c.status == "In Progress" for c in capas), "overdue_capas": 0, "by_severity": {x: sum(r.severity == x for r in rows) for x in severity}, "by_status": {x: sum(r.status == x for r in rows) for x in statuses}, "monthly_trend": [{"month": datetime.utcnow().strftime("%b"), "count": len(rows)}], "capa_completion": {"Open": sum(c.status == "Open" for c in capas), "In Progress": sum(c.status == "In Progress" for c in capas), "Completed": sum(c.status == "Completed" for c in capas)}}


@app.get("/api/reports/analytics")
def reports_analytics(db: Session = Depends(get_db)):
    return dashboard_summary(db)
