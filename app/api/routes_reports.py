#HTTP surface for the pipeline: start a run, poll it, read the report, decide an order.
#
#Why a run is asynchronous. summarize is one LLM call, but agent_reason and draft_recommendations
#each loop per patient — an 8-patient board is 1 + 8 + 8 = 17 sequential calls. Holding a request
#open for that is what routes_ingest.py's header warned against, so POST /boards/{id}/run starts a
#background thread and returns immediately; the client polls GET /reports/{visit_id}.
#
#Run status lives in SQLite (persistence.runs), not in a module dict, so a uvicorn reload doesn't
#strand a client polling a run nobody is tracking any more.

from __future__ import annotations

import threading
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.routes_ingest import _handle
from app.approval import gate
from app.services import persistence
from app.services.persistence import RunStatus

router = APIRouter()

# There is no auth in this app — sign-in was removed as not viable yet. gate.py records who made
# each decision for the audit trail, so decisions from the UI are attributed to this placeholder
# rather than to a real clinician. Replace it the moment a login exists; do NOT let it quietly
# become a real-looking name in the audit log.
UI_CLINICIAN_ID = "ui-unauthenticated"


def visit_id_for(board_id: int) -> str:
    # Must match fetch_board, which is what actually writes the record.
    return f"board-{board_id}"


class RunRequest(BaseModel):
    # Optional pasted meeting transcript. When absent the pipeline synthesizes one from the
    # structured board payload (see fetch_board.build_transcript).
    transcript: Optional[str] = None


class DecisionRequest(BaseModel):
    clinician_id: Optional[str] = None
    reason: str = ""


def _run_pipeline(board_id: int, visit_id: str, transcript: Optional[str]) -> None:
    """Execute the graph on a background thread and record how it ended.

    Imported here rather than at module scope: app.pipeline.graph pulls in app.pipeline.llm, which
    constructs the OpenAI client at import. Keeping it local means the API still starts (and the
    read-only routes still work) when OPENAI_API_KEY is unset.
    """
    try:
        from app.pipeline.graph import build_graph

        initial: dict[str, Any] = {"board_id": board_id}
        if transcript and transcript.strip():
            initial["transcript_override"] = transcript

        state = build_graph().invoke(initial)

        if state.get("report") is None:
            # governance_check refused the board, so assemble_report never ran.
            persistence.finish_run(
                visit_id,
                RunStatus.halted,
                state.get("halt_reason") or "the pipeline produced no report",
            )
            return

        persistence.finish_run(visit_id, RunStatus.ready)
    except Exception as exc:  # noqa: BLE001 — the status row is the only place this can surface
        persistence.finish_run(visit_id, RunStatus.failed, f"{type(exc).__name__}: {exc}")


@router.post("/boards/{board_id}/run")
def run_board(board_id: int, body: RunRequest | None = None):
    visit_id = visit_id_for(board_id)

    existing = persistence.get_run(visit_id)
    if existing and existing["status"] == RunStatus.running.value:
        # Re-running mid-flight would race two threads onto the same visit_id record.
        raise HTTPException(status_code=409, detail=f"a run for {visit_id} is already in progress")

    transcript = body.transcript if body else None
    persistence.start_run(visit_id, board_id)

    thread = threading.Thread(
        target=_run_pipeline, args=(board_id, visit_id, transcript), daemon=True
    )
    thread.start()

    return {"visit_id": visit_id, "run_status": RunStatus.running.value}


@router.get("/reports")
def list_reports():
    return persistence.list_runs()


def _with_live_orders(record: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return the stored report with its recommendations refreshed from the live order list.

    assemble_report copies the orders into the report at build time, so the copy freezes at
    pending_approval. Every later approve/reject writes to record["orders"] instead, which meant a
    decided order still rendered as undecided (with live Yes/No buttons) after a reload. The two
    are the same list — assemble_report literally assigns recommendations = orders — so the live
    list is a drop-in replacement, and orders stay the single source of truth for status.
    """
    report = record.get("report")
    if report is None:
        return None
    return {**report, "recommendations": record.get("orders", report.get("recommendations", []))}


@router.get("/reports/{visit_id}")
def get_report(visit_id: str):
    run = persistence.get_run(visit_id)
    record = persistence.get(visit_id) or {}
    report = _with_live_orders(record)

    if run is None and report is None:
        raise HTTPException(status_code=404, detail=f"no run or report for {visit_id}")

    # A run started from the CLI leaves a report but no runs row, so an existing report wins over
    # a missing status rather than reporting the visit as unknown.
    if run is None:
        return {"run_status": RunStatus.ready.value, "report": report}

    status = run["status"]
    if status == RunStatus.running.value:
        return {"run_status": status, "started_at": run["started_at"]}
    if status == RunStatus.failed.value:
        return {"run_status": status, "error": run["error"]}
    if status == RunStatus.halted.value:
        return {"run_status": status, "halt_reason": run["error"]}

    if report is None:
        raise HTTPException(status_code=404, detail=f"run for {visit_id} finished without a report")
    return {"run_status": RunStatus.ready.value, "report": report}


def _decide(decide, visit_id: str, order_id: str, *args: Any) -> dict[str, Any]:
    # gate.py raises KeyError for an unknown order and ValueError for one that has already been
    # decided. Both are the caller's problem, not a 500.
    try:
        return decide(visit_id, order_id, *args)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/visits/{visit_id}/orders/{order_id}/approve")
def approve(visit_id: str, order_id: str, body: DecisionRequest | None = None):
    clinician = (body.clinician_id if body else None) or UI_CLINICIAN_ID
    return _decide(gate.approve_order, visit_id, order_id, clinician)


@router.post("/visits/{visit_id}/orders/{order_id}/reject")
def reject(visit_id: str, order_id: str, body: DecisionRequest | None = None):
    clinician = (body.clinician_id if body else None) or UI_CLINICIAN_ID
    reason = body.reason if body else ""
    return _decide(gate.reject_order, visit_id, order_id, clinician, reason)
