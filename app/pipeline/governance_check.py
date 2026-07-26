#Front-end gate: check consent/governance on the incoming board before any processing happens.
#Routes to summarize (proceed) or halt (bail out). Non-LLM — a deterministic policy check.
#LangGraph node; returns only the keys it updates.

from __future__ import annotations

from typing import Any

from app.pipeline.state import PipelineState


def governance_check(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    problems: list[str] = []

    board = state.get("board") or {}
    if board.get("status") != "Completed":
        problems.append(f"board status '{board.get('status')}' is not 'Completed'")
    if not state.get("consent_to_process", False):
        problems.append("consent_to_process is not granted")
    if not state.get("patients"):
        problems.append("no patients on the board")

    if problems:
        reason = "; ".join(problems)
        return {
            "governance_ok": False,
            "halt_reason": reason,
            "audit_log": audit + [f"governance_check: FAILED — {reason}"],
        }
    return {
        "governance_ok": True,
        "audit_log": audit + ["governance_check: passed"],
    }


def route_after_governance(state: PipelineState) -> str:
    # Conditional edge: proceed to summarize, or bail out to halt.
    return "summarize" if state.get("governance_ok") else "halt"
