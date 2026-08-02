#Shared LangGraph state for the visit-processing pipeline.
#Lives in its own module so nodes and graph.py can import it without a circular import.

from __future__ import annotations

from typing import Any, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    # Plain fields, last-write-wins (no reducers). Nodes return partial updates and
    # concatenate list fields themselves — consistent with how summarize() already works.

    transcript: list[Any]           # seeded input to summarize
    patients: list[Any]             # board patient diagnostics (seeded upstream by fetch_board)
    board: dict[str, Any]           # board metadata (seeded upstream by fetch_board)
    participants: list[Any]         # board participants (seeded upstream) — for doctors_attended
    events: list[Any]               # board events (seeded upstream) — for start/end time
    consent_to_process: bool        # governance: may we process this board?
    visit_id: str                   # persistence key used by store_and_gate
    transcript_id: str              # ref to the source transcript (pass-through; may be absent)
    note: dict[str, Any]            # produced by summarize (Call A)

    fetched: list[dict[str, Any]]   # accumulated FHIR read results
    fetch_request: Optional[dict[str, Any]]  # pending {resource, params} emitted by agent_reason
    fetch_count: int                # number of fetches performed (drives the loop cap)
    decision: str                   # last action: "fetch" | "proceed" (read by the router)

    recommendations: list[Any]      # produced by draft_recommendations
    report: dict[str, Any]          # produced by assemble_report (the full report object)
    gate_status: str                # set by store_and_gate ("pending_approval") or halt ("halted")
    governance_ok: bool             # set by governance_check; routes summarize vs halt
    halt_reason: str                # why the run was halted (governance failure)
    audit_log: list[str]
