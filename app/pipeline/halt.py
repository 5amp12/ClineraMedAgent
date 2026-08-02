#Terminal bail-out node. Reached when governance_check fails: records why the run stopped and ends.
#LangGraph node; returns only the keys it updates.

from __future__ import annotations

from typing import Any

from app.pipeline.state import PipelineState


def halt(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    reason = state.get("halt_reason") or "unspecified"
    return {
        "gate_status": "halted",
        "audit_log": audit + [f"halt: pipeline stopped — {reason}"],
    }
