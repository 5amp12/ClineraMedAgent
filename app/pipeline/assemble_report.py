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


def _patient_ref(p: dict[str, Any]) -> dict[str, Any]:
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

    patients = state.get("patients") or []

    report = {
        "id": visit_id,
        "report": _clinical(state.get("note") or {}),
        # The FIRST board patient only — kept because the frontend reads report.patient (singular).
        "patient": _patient_ref(patients[0] if patients else {}),
        # Every patient discussed, so each order's patient_id is resolvable from the report alone.
        "patients": [_patient_ref(p) for p in patients],
        "board_id": board.get("id"),
        "board_title": board.get("title"),
        "transcript_id": state.get("transcript_id"),
        # Names, not bare ids — this is rendered as an attendee list, and "6" tells a reader
        # nothing. id is kept alongside so a consumer can still key off it.
        "doctors_attended": [
            {"id": p.get("id"), "name": p.get("name"), "title": p.get("title")}
            for p in (state.get("participants") or [])
        ],
        # No `transcript` field. The segments exist in pipeline state, but neither UI consumer can
        # use them as-is: ClinicalNote keys segments by a `.index` they don't carry, and the
        # Transcript tab renders timestamped {time, title, body} chapters, which is a different
        # artifact we have no meeting timestamps to build (every board returns zero events).
        # Left out rather than shipped in a shape nothing reads.
        "date": (board_date or "")[:10] or None,
        "start_time": min(times) if times else board_date,
        "end_time": max(times) if times else board_date,
        "recommendations": orders,
        "status": state.get("gate_status"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": MODEL,
        "provenance": list(audit),
        # What actually informed the recommendations: agent_reason's per-patient triage, each entry
        # stamped with patient_id/patient_name. Includes the gaps it could not resolve, since
        # nothing can resolve them automatically. (Previously this carried FHIR read results from
        # the mock fetch loop.)
        "supporting_data": state.get("assessments", []),
    }

    persistence.attach_report(visit_id, report)

    return {
        "report": report,
        "audit_log": audit + ["assemble_report: report built"],
    }
