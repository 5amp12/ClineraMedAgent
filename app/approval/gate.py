#Approval state machine (the "gate"). A clinician approves or rejects a stored order; approving
#triggers the FHIR write with the clinician as requester. Runs out-of-band from the graph — the
#pipeline has already ended with the orders persisted as pending_approval.

from __future__ import annotations

from typing import Any

from app.services import fhir_client, persistence
from app.services.persistence import OrderStatus


def _load_pending(visit_id: str, order_id: str) -> dict[str, Any]:
    order = persistence.find_order(visit_id, order_id)
    if order is None:
        raise KeyError(f"order {order_id} not found for visit {visit_id}")
    if order["status"] != OrderStatus.pending_approval.value:
        raise ValueError(f"order {order_id} is '{order['status']}', not pending_approval")
    return order


def approve_order(visit_id: str, order_id: str, clinician_id: str) -> dict[str, Any]:
    order = _load_pending(visit_id, order_id)

    persistence.set_order_status(visit_id, order_id, OrderStatus.approved, approved_by=clinician_id)
    result = fhir_client.write_order(order, requester=clinician_id)
    final = OrderStatus.written if result["ok"] else OrderStatus.write_failed
    return persistence.set_order_status(visit_id, order_id, final, fhir=result)


def reject_order(visit_id: str, order_id: str, clinician_id: str, reason: str = "") -> dict[str, Any]:
    _load_pending(visit_id, order_id)
    return persistence.set_order_status(
        visit_id, order_id, OrderStatus.rejected, rejected_by=clinician_id, reason=reason
    )
