"""Professional, data-backed RCA report rendering."""
from __future__ import annotations

from datetime import datetime
import textwrap
from typing import Any

import fitz


NAVY = (0.043, 0.114, 0.224)
BLUE = (0.09, 0.412, 0.878)
INK = (0.09, 0.15, 0.24)
MUTED = (0.34, 0.41, 0.51)
LIGHT = (0.94, 0.965, 0.99)


def build_investigation_report(data: dict[str, Any]) -> bytes:
    document = fitz.open()
    page_number = 0
    page: fitz.Page
    y = 0.0

    def new_page() -> None:
        nonlocal page, page_number, y
        page_number += 1
        page = document.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(0, 0, 595, 58), color=NAVY, fill=NAVY)
        page.insert_text((42, 34), "PHARMARCA", fontsize=15, fontname="hebo", color=(1, 1, 1))
        page.insert_text((42, 49), "AI QUALITY PLATFORM  |  RCA INVESTIGATION REPORT", fontsize=7, fontname="hebo", color=(0.72, 0.82, 0.95))
        page.draw_line((42, 796), (553, 796), color=(0.8, 0.85, 0.91), width=0.5)
        page.insert_text((42, 812), "AI-assisted draft — subject to investigator and QA review", fontsize=7, color=MUTED)
        page.insert_text((510, 812), f"Page {page_number}", fontsize=7, color=MUTED)
        y = 82

    def space(height: float) -> None:
        nonlocal y
        if y + height > 780:
            new_page()

    def heading(value: str) -> None:
        nonlocal y
        space(28)
        page.draw_rect(fitz.Rect(42, y, 553, y + 19), color=LIGHT, fill=LIGHT)
        page.insert_text((51, y + 13), value.upper(), fontsize=9, fontname="hebo", color=BLUE)
        y += 29

    def paragraph(value: Any, bold: bool = False) -> None:
        nonlocal y
        text = str(value or "Not provided.")
        lines: list[str] = []
        for raw in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw, width=93) or [""])
        for line in lines:
            space(13)
            page.insert_text((48, y), line, fontsize=8.5, fontname="hebo" if bold else "helv", color=INK)
            y += 12
        y += 3

    def fields(rows: list[tuple[str, Any]]) -> None:
        nonlocal y
        for label, value in rows:
            if value in (None, "", {}, []):
                continue
            rendered = ", ".join(f"{key}: {item}" for key, item in value.items()) if isinstance(value, dict) else str(value)
            wrapped = textwrap.wrap(rendered, width=66) or ["Not provided."]
            space(max(17, 12 * len(wrapped)))
            page.insert_text((48, y), label, fontsize=8, fontname="hebo", color=MUTED)
            page.insert_text((175, y), wrapped[0], fontsize=8.5, color=INK)
            for continuation in wrapped[1:]:
                y += 11
                page.insert_text((175, y), continuation, fontsize=8.5, color=INK)
            y += 15

    def records(items: list[dict[str, Any]], title_key: str, body_keys: list[str]) -> None:
        nonlocal y
        if not items:
            paragraph("Not available.")
            return
        for index, item in enumerate(items, 1):
            label = item.get(title_key) or f"Item {index}"
            paragraph(f"{index}. {label}", bold=True)
            for key in body_keys:
                if item.get(key):
                    paragraph(f"{key.replace('_', ' ').title()}: {item[key]}")

    new_page()
    page.draw_rect(fitz.Rect(42, 92, 553, 192), color=LIGHT, fill=LIGHT)
    page.insert_text((62, 124), "ROOT CAUSE ANALYSIS", fontsize=20, fontname="hebo", color=NAVY)
    page.insert_text((62, 149), data.get("title") or "Investigation report", fontsize=11, fontname="hebo", color=INK)
    page.insert_text((62, 174), f"RCA ID: {data.get('investigation_no', 'Not assigned')}  |  Generated: {datetime.now():%d %B %Y}", fontsize=8.5, color=MUTED)
    y = 220

    heading("Investigation overview")
    fields([
        ("Status", data.get("status")),
        ("Product / API", data.get("product_name")),
        ("Batch number", data.get("batch_number")),
        ("Deviation category", data.get("incident_category")),
        ("Department", data.get("department")),
        ("Manufacturing date", data.get("manufacturing_date")),
        ("Affected quantity", data.get("affected_quantity")),
        ("Equipment", data.get("equipment_id")),
    ])

    heading("Deviation and containment")
    paragraph(data.get("deviation_description"))
    fields([("Immediate containment", data.get("containment_actions")), ("Batch disposition", data.get("batch_disposition"))])

    heading("Expected versus actual parameters")
    fields([("Expected", data.get("expected_parameters")), ("Actual", data.get("actual_parameters"))])

    risk = data.get("risk_assessment") or {}
    heading("Initial impact assessment")
    fields([("Risk level", risk.get("level")), ("Rationale", risk.get("rationale")), ("Patient impact", risk.get("patient_impact")), ("Product impact", risk.get("product_impact")), ("Recommendation", risk.get("recommendation"))])

    if data.get("five_whys"):
        heading("Five Whys analysis")
        records(data["five_whys"], "why", ["answer"])
    if data.get("fishbone"):
        heading("Fishbone analysis")
        for category, factors in data["fishbone"].items():
            paragraph(f"{category}: {', '.join(factors)}")
    if data.get("root_causes"):
        heading("Potential root causes")
        records(data["root_causes"], "description", ["category", "confidence", "supporting_evidence", "contradictory_evidence", "verification_requirements"])
    if data.get("evidence_gaps"):
        heading("Evidence gaps")
        records(data["evidence_gaps"], "description", ["rationale"])
    if data.get("capa_actions"):
        heading("CAPA recommendations")
        records(data["capa_actions"], "description", ["action_type", "priority", "responsible_department", "justification", "effectiveness_criteria", "status"])

    heading("Conclusion and current status")
    paragraph("This report reflects the latest saved investigation information. Findings, root-cause hypotheses, evidence requests, and CAPA recommendations remain subject to qualified investigator and QA review unless explicitly approved in the investigation record.")
    fields([("Current investigation status", data.get("status")), ("CAPA recommendations", len(data.get("capa_actions") or []))])
    return document.tobytes(garbage=4, deflate=True)
