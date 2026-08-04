#Pushes the board's AI summary back to Clinera (POST /api/board-ai-summaries).
#
#Shape follows the integration guide's example: title, executive_overview, key_decisions
#(patientId + decision), topics_discussed, generated_at. `data.summary` is typed "JSON / Any", so
#the shape is not enforced server-side — we match the documented example so it reads the way
#Clinera's own consumers expect.
#
#Fires when a clinician decides an order, NOT at pipeline end: an unreviewed AI proposal is not a
#board decision, and publishing one as the board's official summary would bypass the approval gate
#the pipeline exists to enforce. The endpoint upserts 1-to-1 per board, so re-pushing after each
#decision overwrites rather than accumulating.
#
#Deliberately NOT sent: `provenance` (our internal audit log), `supporting_data` (internal triage),
#and the singular `patient` field, which is only the first board patient and would misdescribe a
#multi-patient board.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services import clinera_client, persistence
from app.services.persistence import OrderStatus

SUMMARIES_PATH = "/api/board-ai-summaries"
BY_BOARD_PATH = "/api/board-ai-summaries/by-board/{board_id}"

# Statuses that mean a clinician actually decided something.
_DECIDED = {OrderStatus.approved.value, OrderStatus.rejected.value,
            OrderStatus.published.value, OrderStatus.publish_failed.value}


def _now() -> str:
    # The guide's format ("2026-07-28T12:00:00.000Z"), not isoformat's "+00:00".
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _decision_text(order: dict[str, Any]) -> str:
    detail = order.get("details", "")
    if order.get("status") == OrderStatus.rejected.value:
        reason = order.get("reason")
        return f"Rejected: {detail}" + (f" ({reason})" if reason else "")
    return f"Approved: {detail}"


def build_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Map a persisted visit record onto the summary shape from the integration guide."""
    report = record.get("report") or {}
    # summarize's output, as copied onto the report by assemble_report.
    note = report.get("report") or record.get("note") or {}
    orders = record.get("orders") or []

    decided = [o for o in orders if o.get("status") in _DECIDED]

    # Distinct diagnoses across the board, order preserved.
    topics: list[str] = []
    for patient in report.get("patients") or []:
        diagnosis = patient.get("diagnosis")
        if diagnosis and diagnosis not in topics:
            topics.append(diagnosis)

    return {
        "title": report.get("board_title") or record.get("visit_id"),
        "executive_overview": note.get("reason_for_visit"),
        # Counted here, not taken from the model's prose. On board 892 the LLM wrote "reviewed 10
        # cases" against 8 actual patients, on two independent runs — a number the code already
        # knows should never be inferred.
        "case_count": len(report.get("patients") or []),
        "key_decisions": [
            {"patientId": o.get("patient_id"), "decision": _decision_text(o)}
            for o in decided
        ],
        "topics_discussed": topics,
        "generated_at": _now(),
        # Beyond the documented example, but the field is free-form and this is the reasoning
        # behind each decision above.
        #
        # DECIDED ORDERS ONLY. Orders still pending_approval are never sent: they are model
        # proposals no clinician has reviewed, and publishing them into Clinera's board record
        # would defeat the point of pushing on approval rather than at pipeline end. It also
        # keeps the payload proportional to decisions made rather than to board size — sending
        # all 25 orders on board 892 was 11.7 KB, of which 93% was unreviewed proposals.
        "decisions": [
            {
                "patientId": o.get("patient_id"),
                "patient_name": o.get("patient_name"),
                "order_type": o.get("order_type"),
                "details": o.get("details"),
                "rationale": o.get("rationale"),
                "confidence": o.get("confidence"),
                "status": o.get("status"),
                "decided_by": o.get("approved_by") or o.get("rejected_by"),
            }
            for o in decided
        ],
        "generated_by": report.get("generated_by"),
    }


def publish_board_summary(visit_id: str) -> dict[str, Any]:
    """Build and POST the board summary.

    Returns {"ok": bool, ...} rather than raising: a publish failure must downgrade the order's
    status, not discard the clinician's approval.
    """
    record = persistence.get(visit_id)
    if record is None:
        return {"ok": False, "reason": f"no persisted record for {visit_id}"}

    board_id = (record.get("report") or {}).get("board_id")
    if board_id is None:
        return {"ok": False, "reason": "record has no report/board_id; run the pipeline first"}

    try:
        response = clinera_client.post_json(
            SUMMARIES_PATH,
            {"data": {"board": board_id, "summary": build_summary(record)}},
        )
    except Exception as exc:  # network, auth, 4xx/5xx — the approval itself still stands
        return {"ok": False, "board_id": board_id, "reason": f"{type(exc).__name__}: {exc}"}

    return {"ok": True, "board_id": board_id, "response": response}


def fetch_board_summary(board_id: int) -> Any:
    """Read back what Clinera holds for this board. Returns None when none exists — the guide
    documents that as 200 with data: null, not a 404."""
    response = clinera_client.get_json(BY_BOARD_PATH.format(board_id=board_id))
    return (response or {}).get("data")
