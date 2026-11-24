"""LangGraph workflow with a deterministic fallback for validated demo operation."""
from __future__ import annotations
import re
from typing import Any, TypedDict
from langgraph.graph import END, StateGraph
from .config import get_settings
from .schemas import InvestigationFields

settings = get_settings()

# Some environments bundle LangChain 1.x alongside LangGraph 0.2.x. LangGraph
# itself only needs the legacy global flags; defining them keeps the compiled
# StateGraph usable without forcing an unrelated application-wide downgrade.
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except ImportError:
    pass


class RCAState(TypedDict, total=False):
    message: str
    context: dict[str, Any]
    intent: str
    fields: dict[str, Any]
    changed_fields: list[str]
    risk_assessment: dict[str, Any]
    evidence_gaps: list[dict[str, str]]
    root_causes: list[dict[str, Any]]
    five_whys: list[dict[str, str]]
    fishbone: dict[str, list[str]]
    capas: list[dict[str, Any]]
    response: str


def _value(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip(" .,:;") if match else None


def route(state: RCAState) -> RCAState:
    text = state["message"].lower()
    # Uploaded documents can legitimately contain phrases such as "root cause"
    # or "CAPA". Extraction must take priority so form fields are populated
    # before a user explicitly requests an analysis.
    if state.get("context", {}).get("document_text"): intent = "extract_document"
    elif any(x in text for x in ["5 why", "five why", "fishbone", "root cause", "ishikawa"]): intent = "run_rca"
    elif any(x in text for x in ["missing evidence", "evidence gap", "what evidence", "additional evidence"]): intent = "find_gaps"
    elif any(x in text for x in ["capa", "corrective action", "preventive action"]): intent = "generate_capa"
    elif any(x in text for x in ["correction", "correct:", "update", "change batch", "batch number is"]): intent = "edit"
    # A conversational message is not incident data. Keeping it on its own
    # route prevents greetings from re-running document-style extraction.
    elif any(x in text for x in ["deviation", "incident", "oos", "out of specification", "batch", "temperature", "moisture", "result"]): intent = "create"
    else: intent = "chat"
    return {"intent": intent}


def extract(state: RCAState) -> RCAState:
    text = state["message"]
    existing = state.get("context", {}).get("fields", {})
    fields: dict[str, Any] = {}
    def labeled(*labels: str) -> str | None:
        joined = "|".join(re.escape(label) for label in labels)
        return _value(rf"(?m)^\s*(?:{joined})\s*:\s*([^\n]+)", text)

    product = labeled("Product", "Product / API", "API name") or _value(r"(?:manufacturing of|product(?:/api)?(?: is|:)?|api(?: is|:)?)[\s]+([A-Za-z0-9()\- /]+?)(?:\s+(?:api )?batch|,|\.)", text)
    batch = labeled("Batch", "Batch number", "Lot number") or _value(r"(?:batch(?: number)?(?: is|:)?|batch\s+)\s*([A-Za-z0-9\-]+)", text)
    equipment = _value(r"(?:equipment(?: id)?(?: is|:)?|reactor(?: id)?(?: is|:)?)\s*([A-Z]+(?:-| )[A-Z0-9]+|REACTOR-?\d+)", text)
    stage = _value(r"(?:during(?: the)?\s+|stage(?: is|:)?\s*)(reaction|crystallization|drying|milling|filtration|charging|granulation)(?:\s+stage)?", text)
    actual = _value(r"(?:reached|actual(?: temperature)?(?: was|:)?|temperature(?: exceeded)?[^0-9]{0,15})\s*(\d{1,3}\s*°?C)", text)
    expected = _value(r"(?:approved range of|expected(?: range)?(?: is|:)?|limit(?: is|:)?)\s*(\d{1,3}\s*(?:-|to)\s*\d{1,3}\s*°?C)", text)
    duration = _value(r"(?:for approximately|for)(\s*\d+\s*(?:minutes|min|hours|hrs))", text)
    quantity = labeled("Affected quantity", "Quantity affected") or _value(r"(?:affected quantity(?: is|:)?|quantity(?: is|:)?)\s*(\d+(?:\.\d+)?\s*(?:kg|g|l|litres?)(?:\s*\([^\n]+\))?)", text)
    grade = labeled("Grade", "API grade")
    department = labeled("Department", "Responsible department")
    incident_category = labeled("Incident category", "Deviation category", "Event category")
    manufacturing_date = labeled("Manufacturing date", "Date of manufacture")
    disposition = labeled("Batch disposition", "Disposition")
    equipment_label = labeled("Equipment ID", "Equipment", "Equipment number")
    stage_label = labeled("Manufacturing stage", "Process stage", "Stage")
    date = labeled("Deviation date", "Incident date")
    reported_result = labeled("Reported result", "Actual result", "Actual process parameter", "Moisture content")
    specification = labeled("Approved specification limit", "Expected process parameter", "Expected limit", "Moisture specification limit")
    if product: fields["product_name"] = product
    if batch: fields["batch_number"] = batch
    if equipment: fields["equipment_id"] = equipment.replace(" ", "-")
    if stage: fields["manufacturing_stage"] = stage.title()
    if quantity: fields["affected_quantity"] = quantity
    if grade: fields["api_grade"] = grade
    if department: fields["department"] = department
    if incident_category: fields["incident_category"] = incident_category
    if manufacturing_date: fields["manufacturing_date"] = manufacturing_date
    if disposition: fields["batch_disposition"] = disposition
    if equipment_label: fields["equipment_id"] = equipment_label
    if stage_label: fields["manufacturing_stage"] = stage_label
    if date: fields["deviation_date"] = date
    if expected: fields["expected_parameters"] = {"Temperature": expected}
    if actual: fields["actual_parameters"] = {"Temperature": actual, **({"Duration": duration} if duration else {})}
    # Support QC/OOS records (for example moisture content) as well as process
    # excursions. The parameter name is taken from the report, never invented.
    moisture_result = _value(r"(?im)^\s*moisture\s+content\s*:\s*([0-9][0-9.,]*\s*%)", text)
    moisture_limit = _value(r"(?im)^\s*(?:approved\s+)?(?:specification\s+)?(?:limit|moisture\s+specification\s+limit)\s*:\s*([0-9][0-9.,]*\s*%)", text)
    if moisture_result:
        fields["actual_parameters"] = {"Moisture content": moisture_result}
        if moisture_limit: fields["expected_parameters"] = {"Moisture content": moisture_limit}
    elif reported_result:
        result_match = re.match(r"([A-Za-z][A-Za-z /-]*?)\s+([0-9][0-9.,]*\s*%?)$", reported_result.strip())
        if result_match:
            parameter = result_match.group(1).strip().title()
            fields["actual_parameters"] = {parameter: result_match.group(2).strip()}
            if specification: fields["expected_parameters"] = {parameter: specification}
    containment = labeled("Containment actions", "Immediate containment actions")
    if containment: fields["containment_actions"] = containment
    if state["intent"] in ("create", "extract_document") and text:
        fields["deviation_description"] = text[:1500]
        fields["title"] = f"Deviation investigation – {fields.get('batch_number', existing.get('batch_number', 'new investigation'))}"
    changed = list(fields)
    return {"fields": fields, "changed_fields": changed}


def validate(state: RCAState) -> RCAState:
    fields = state.get("fields", {})
    context = state.get("context", {}).get("fields", {})
    actual_parameters = fields.get("actual_parameters", {}) or context.get("actual_parameters", {}) or {}
    expected_parameters = fields.get("expected_parameters", {}) or context.get("expected_parameters", {}) or {}
    actual = next(iter(actual_parameters.values()), "")
    expected = next(iter(expected_parameters.values()), "")
    actual_number = _value(r"([0-9]+(?:\.[0-9]+)?)", str(actual))
    expected_number = _value(r"([0-9]+(?:\.[0-9]+)?)", str(expected))
    exceeds_limit = bool(actual_number and expected_number and float(actual_number) > float(expected_number))
    if exceeds_limit:
        risk = {"level": "High", "rationale": "The reported result exceeds the stated specification limit. This is an initial, reviewable assessment only.", "patient_impact": "Not assessed; not provided.", "product_impact": "Potential product-quality impact; source-record and analytical review are required.", "recommendation": "Maintain qualified QA control until records are reviewed and an approved disposition is made."}
    else:
        risk = {"level": "Pending", "rationale": "Insufficient verified process parameter information for a risk classification.", "patient_impact": "Not assessed", "product_impact": "Not assessed", "recommendation": "Provide approved limits, actual readings, and batch impact information."}
    return {"risk_assessment": risk}


def evidence_analysis(state: RCAState) -> RCAState:
    text = (state.get("context", {}).get("document_text") or state.get("message", "")).lower()
    if "moisture" in text:
        return {"evidence_gaps": [
            {"description": "Original laboratory results and chromatograms", "rationale": "Verifies the reported moisture result and analytical calculation."},
            {"description": "Approved batch manufacturing record", "rationale": "Establishes the executed process and any documented deviations."},
            {"description": "Drying-process parameters and trends", "rationale": "Assesses drying performance without presuming a failure."},
            {"description": "Drying equipment maintenance, calibration, and vacuum records", "rationale": "Tests equipment and vacuum hypotheses using objective records."},
            {"description": "Environmental humidity, sampling, and analytical-method verification records", "rationale": "Assesses environmental, sampling, and method-related hypotheses."},
        ]}
    return {"evidence_gaps": [
        {"description": "Approved batch manufacturing record", "rationale": "Establishes what was executed and any documented deviations."},
        {"description": "Original laboratory or process source records", "rationale": "Verifies the reported observation before drawing conclusions."},
        {"description": "Equipment maintenance and calibration records", "rationale": "Tests equipment-related hypotheses using objective evidence."},
    ]}


def rca(state: RCAState) -> RCAState:
    return {"five_whys": [
        {"why": "Why was the reported result outside the stated specification?", "answer": "Not established; source records and the investigation avenues must be reviewed."},
        {"why": "What process, equipment, material, sampling, or method factors could contribute?", "answer": "Potential contributors remain hypotheses until supported by qualified evidence."},
    ], "fishbone": {"People": ["Sampling and execution records to be reviewed"], "Machine": ["Equipment condition and maintenance records to be reviewed"], "Method": ["Approved process and analytical method execution to be reviewed"], "Material": ["Raw material characteristics to be reviewed"], "Measurement": ["Laboratory source records and method verification to be reviewed"], "Environment": ["Environmental conditions to be reviewed"]}, "root_causes": [{"category": "Investigation status", "description": "Root cause not established; qualified evidence review is required.", "confidence": "Not established", "supporting_evidence": "A deviation or out-of-specification result was reported.", "contradictory_evidence": "No source records establishing a causal mechanism were supplied.", "verification_requirements": "Review the applicable batch, laboratory, equipment, environmental, sampling, and method records.", "confirmed": False}]}


def capa(state: RCAState) -> RCAState:
    return {"capas": [
        {"action_type": "Correction", "description": "Maintain documented control of the affected batch pending qualified QA assessment.", "priority": "High", "responsible_department": "Quality Assurance", "suggested_owner": None, "target_date": None, "justification": "Preserves batch control while evidence is verified.", "effectiveness_criteria": "QA-approved assessment and disposition decision.", "status": "Pending Review"},
        {"action_type": "Corrective Action", "description": "Complete the evidence review and implement only actions supported by the confirmed investigation outcome.", "priority": "High", "responsible_department": "Quality Assurance", "suggested_owner": None, "target_date": None, "justification": "No root cause is established yet.", "effectiveness_criteria": "Approved investigation conclusion with documented actions, if needed.", "status": "Pending Review"},
        {"action_type": "Preventive Action", "description": "After the investigation conclusion, assess whether related procedures, monitoring, or training require preventive revision.", "priority": "Medium", "responsible_department": "Quality Assurance", "suggested_owner": None, "target_date": None, "justification": "Prevention should be linked to verified recurrence risk, not an unconfirmed cause.", "effectiveness_criteria": "Approved change assessment and documented effectiveness plan, if applicable.", "status": "Pending Review"},
    ]}


def assemble(state: RCAState) -> RCAState:
    intent = state["intent"]
    if intent == "edit": response = "I applied only the identified correction fields. Please review the highlighted suggestions before confirming."
    elif intent in ("create", "extract_document"): response = "I extracted the available incident information and prepared reviewable suggestions. Missing details are intentionally left blank."
    elif intent == "run_rca": response = "I generated hypothesis-level 5 Whys, Fishbone factors, and verification requirements. No root cause is confirmed."
    elif intent == "find_gaps": response = "I identified the evidence needed to verify the current hypotheses."
    elif intent == "generate_capa": response = "I generated reviewable CAPA recommendations linked to the current working hypothesis."
    else: response = "Please upload an investigation PDF, describe a deviation, or use the RCA, Evidence gaps, or CAPA actions when the draft has enough context."
    return {"response": response}


def build_graph():
    graph = StateGraph(RCAState)
    graph.add_node("intent_router", route)
    graph.add_node("document_processing", lambda s: s)
    graph.add_node("information_extraction", extract)
    graph.add_node("information_validation", validate)
    graph.add_node("evidence_analysis", evidence_analysis)
    graph.add_node("root_cause_analysis", rca)
    graph.add_node("missing_evidence_detection", evidence_analysis)
    graph.add_node("capa_recommendation", capa)
    graph.add_node("response_assembly", assemble)
    graph.set_entry_point("intent_router")
    graph.add_conditional_edges("intent_router", lambda s: s["intent"], {"create": "information_extraction", "edit": "information_extraction", "extract_document": "document_processing", "run_rca": "root_cause_analysis", "find_gaps": "missing_evidence_detection", "generate_capa": "capa_recommendation", "chat": "response_assembly"})
    graph.add_edge("document_processing", "information_extraction")
    graph.add_edge("information_extraction", "information_validation")
    graph.add_edge("information_validation", "response_assembly")
    graph.add_edge("root_cause_analysis", "response_assembly")
    graph.add_edge("missing_evidence_detection", "response_assembly")
    graph.add_edge("capa_recommendation", "response_assembly")
    graph.add_edge("response_assembly", END)
    return graph.compile()


workflow = build_graph()


def run_analysis(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(workflow.invoke({"message": message, "context": context or {}}))
    # The graph supplies safe defaults. When Groq is configured it enriches the
    # requested extraction or analysis, always as unconfirmed review material.
    if settings.groq_api_key and not settings.demo_mode and result.get("intent") != "chat":
        try:
            from groq import Groq
            import json
            intent = result.get("intent")
            if intent in {"create", "edit", "extract_document"}:
                prompt = """Extract only explicitly stated pharmaceutical investigation facts. Return JSON with one `fields` object. Allowed field keys: title, product_name, api_grade, batch_number, affected_quantity, manufacturing_stage, manufacturing_date, department, incident_category, equipment_id, deviation_date, deviation_description, containment_actions, batch_disposition, expected_parameters, actual_parameters. Omit unknown keys. Do not infer root cause, patient impact, or an approved disposition.\nIncident text:\n""" + message
            elif intent == "run_rca":
                prompt = """Create reviewable, hypothesis-level RCA output from the supplied investigation context. Return JSON with root_causes (list), five_whys (list), and fishbone (object). Each root cause must include category, description, confidence='Hypothesis', supporting_evidence, contradictory_evidence, verification_requirements, confirmed=false. Do not state a root cause as fact when records are missing.\nContext:\n""" + json.dumps(context or {})
            elif intent == "find_gaps":
                prompt = """Identify only evidence records needed to investigate this pharmaceutical incident. Return JSON with evidence_gaps, a list of objects with description and rationale. Treat requests as missing evidence, not proof of failure.\nContext:\n""" + json.dumps(context or {})
            else:
                prompt = """Generate editable, unapproved CAPA recommendations appropriate to the supplied investigation context. Return JSON with capas, each having action_type (Correction, Corrective Action, or Preventive Action), description, priority, responsible_department, suggested_owner, target_date, justification, effectiveness_criteria, and status='Pending Review'. Do not invent people, dates, approvals, effectiveness results, or a repair for an unconfirmed failure.\nContext:\n""" + json.dumps(context or {})
            completion = Groq(api_key=settings.groq_api_key).chat.completions.create(
                model=settings.groq_model,
                messages=[{"role": "system", "content": "You are a pharmaceutical quality assistant. Return valid JSON only; unknown facts must be omitted."}, {"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            extracted = json.loads(completion.choices[0].message.content or "{}")
            if intent in {"create", "edit", "extract_document"}:
                validated = InvestigationFields.model_validate(extracted.get("fields", extracted))
                result["fields"].update(validated.model_dump(exclude_none=True, exclude_defaults=True))
                result["changed_fields"] = list(result["fields"])
            elif intent == "run_rca":
                result["root_causes"] = [item for item in extracted.get("root_causes", []) if isinstance(item, dict)]
                result["five_whys"] = [item for item in extracted.get("five_whys", []) if isinstance(item, dict)]
                result["fishbone"] = extracted.get("fishbone", {}) if isinstance(extracted.get("fishbone"), dict) else {}
            elif intent == "find_gaps":
                result["evidence_gaps"] = [item for item in extracted.get("evidence_gaps", []) if isinstance(item, dict) and item.get("description") and item.get("rationale")]
            else:
                validated_capas = []
                for item in extracted.get("capas", []):
                    if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in ("action_type", "description", "priority", "responsible_department", "justification", "effectiveness_criteria")):
                        continue
                    # The model must not promote a guess to an assignment or
                    # schedule. Those fields remain blank for QA to provide.
                    item = {**item, "suggested_owner": None, "target_date": None, "status": "Pending Review"}
                    validated_capas.append(item)
                result["capas"] = validated_capas
        except Exception as exc:
            # Do not hide a configured provider failure behind invented AI output.
            result.setdefault("warnings", []).append(f"Groq enrichment failed: {type(exc).__name__}. Safe rule-based suggestions remain available for review.")
            result["response"] += " Groq enrichment failed; no Groq-generated findings were applied."
    return result
