#Shared LangGraph state for the visit-processing pipeline.
#Lives in its own module so nodes and graph.py can import it without a circular import.

from __future__ import annotations

from typing import Any, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    # Plain fields, last-write-wins (no reducers). Nodes return partial updates and
    # concatenate list fields themselves — consistent with how summarize() already works.

    transcript: list[Any]           # seeded input to summarize
    patients: list[Any]             # board patient diagnostics (seeded upstream by fetch_board)
    note: dict[str, Any]            # produced by summarize (Call A)

    fetched: list[dict[str, Any]]   # accumulated FHIR read results
    fetch_request: Optional[dict[str, Any]]  # pending {resource, params} emitted by agent_reason
    fetch_count: int                # number of fetches performed (drives the loop cap)
    decision: str                   # last action: "fetch" | "proceed" (read by the router)

    recommendations: list[Any]      # produced by draft_recommendations
    audit_log: list[str]
