#Final node: assemble the full report object (note + patient/board metadata + proposed orders +
#evidence + provenance) and attach it to the persisted record. Non-LLM; runs LAST so it can see
#everything the pipeline produced. LangGraph node — returns only the keys it updates.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.pipeline.llm import MODEL
from app.pipeline.state import PipelineState
from app.services import persistence

_CLINICAL_FIELDS = ("reason_for_visit", "history", "findings", "plan", "source_segments")


def _clinical(note: dict[str, Any]) -> dict[str, Any]:
    return {k: note.get(k) for k in _CLINICAL_FIELDS}


def _patient(patients: list[dict[str, Any]]) -> dict[str, Any]:
    # One report per run -> the primary (first) board patient. Multi-patient boards are future work.
    p = patients[0] if patients else {}
    return {
        "id": p.get("id"),
        "mrn": p.get("mrn"),
        "name": p.get("name"),
        "diagnosis": (p.get("diagnosis_type") or {}).get("display_name"),
    }


def assemble_report(state: PipelineState) -> dict[str, Any]:
    visit_id = state.get("visit_id") or "unknown-visit"
    board = state.get("board") or {}
    board_date = board.get("date")
    audit = state.get("audit_log", [])

    # start/end from event timestamps (ISO strings sort chronologically); fall back to board date.
    times = [e.get("event_timestamp") for e in (state.get("events") or []) if e.get("event_timestamp")]

    # Orders (with their ids + pending_approval status) live on the persisted record.
    orders = (persistence.get(visit_id) or {}).get("orders", [])

    report = {
        "id": visit_id,
        "report": _clinical(state.get("note") or {}),
        "patient": _patient(state.get("patients") or []),
        "board_id": board.get("id"),
        "board_title": board.get("title"),
        "transcript_id": state.get("transcript_id"),
        "doctors_attended": [p.get("id") for p in (state.get("participants") or [])],
        "date": (board_date or "")[:10] or None,
        "start_time": min(times) if times else board_date,
        "end_time": max(times) if times else board_date,
        "recommendations": orders,
        "status": state.get("gate_status"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": MODEL,
        "provenance": list(audit),
        "supporting_data": state.get("fetched", []),
    }

    persistence.attach_report(visit_id, report)

    return {
        "report": report,
        "audit_log": audit + ["assemble_report: report built"],
    }
