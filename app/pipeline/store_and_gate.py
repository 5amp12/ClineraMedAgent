#Final node: persist the note + proposed orders as pending_approval, then end the run. The
#clinician approves/rejects later, out-of-band (see app/approval/gate.py), and that is what
#triggers the FHIR write — the graph never blocks. LangGraph node; returns only the keys it updates.

from __future__ import annotations

from typing import Any

from app.pipeline.state import PipelineState
from app.services import persistence


def store_and_gate(state: PipelineState) -> dict[str, Any]:
    visit_id = state.get("visit_id") or "unknown-visit"
    recommendations = state.get("recommendations", [])
    audit = state.get("audit_log", [])

    persistence.save_pending(visit_id, state.get("note", {}), recommendations)

    return {
        "gate_status": "pending_approval",
        "audit_log": audit
        + [f"store_and_gate: stored {len(recommendations)} orders, pending approval"],
    }
