#Approval state machine (the "gate"). A clinician approves or rejects a stored order; either way
#the board's AI summary is pushed to Clinera so it reflects the decisions actually made. Runs
#out-of-band from the graph — the pipeline has already ended with orders persisted as
#pending_approval.
#
#The push is board-level (one summary per board, upserted 1-to-1), not per-order, so each decision
#re-sends the whole current picture. A failed push downgrades the order to publish_failed but never
#discards the decision itself.

from __future__ import annotations

from typing import Any

from app.services import clinera_publish, persistence
from app.services.persistence import OrderStatus


def _load_pending(visit_id: str, order_id: str) -> dict[str, Any]:
    order = persistence.find_order(visit_id, order_id)
    if order is None:
        raise KeyError(f"order {order_id} not found for visit {visit_id}")
    if order["status"] != OrderStatus.pending_approval.value:
        raise ValueError(f"order {order_id} is '{order['status']}', not pending_approval")
    return order


def _publish(visit_id: str, order_id: str) -> dict[str, Any]:
    result = clinera_publish.publish_board_summary(visit_id)
    final = OrderStatus.published if result["ok"] else OrderStatus.publish_failed
    return persistence.set_order_status(visit_id, order_id, final, clinera=result)


def approve_order(visit_id: str, order_id: str, clinician_id: str) -> dict[str, Any]:
    _load_pending(visit_id, order_id)
    # Record the decision BEFORE publishing, so a failed push leaves an approved order rather than
    # one that looks untouched.
    persistence.set_order_status(visit_id, order_id, OrderStatus.approved, approved_by=clinician_id)
    return _publish(visit_id, order_id)


def reject_order(visit_id: str, order_id: str, clinician_id: str, reason: str = "") -> dict[str, Any]:
    _load_pending(visit_id, order_id)
    persistence.set_order_status(
        visit_id, order_id, OrderStatus.rejected, rejected_by=clinician_id, reason=reason
    )
    # Rejections are published too — deciding not to act is part of the board's record.
    return _publish(visit_id, order_id)
