#In-memory store for draft notes + proposed orders, keyed by visit_id. Tracks each order's status
#through the approval lifecycle. Swap the dict for a real datastore later — the function surface
#stays the same.

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class OrderStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    written = "written"          # FHIR write succeeded
    write_failed = "write_failed"


# visit_id -> record
_STORE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_pending(visit_id: str, note: dict[str, Any],
                 recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    orders = [
        {**rec, "id": f"{visit_id}-ord-{i}", "status": OrderStatus.pending_approval.value}
        for i, rec in enumerate(recommendations, start=1)
    ]
    record = {"visit_id": visit_id, "note": note, "orders": orders, "created_at": _now()}
    _STORE[visit_id] = record
    return record


def get(visit_id: str) -> Optional[dict[str, Any]]:
    return _STORE.get(visit_id)


def find_order(visit_id: str, order_id: str) -> Optional[dict[str, Any]]:
    record = _STORE.get(visit_id)
    if not record:
        return None
    return next((o for o in record["orders"] if o["id"] == order_id), None)


def list_pending() -> list[dict[str, Any]]:
    return [
        r for r in _STORE.values()
        if any(o["status"] == OrderStatus.pending_approval.value for o in r["orders"])
    ]


def set_order_status(visit_id: str, order_id: str, status: OrderStatus,
                     **extra: Any) -> dict[str, Any]:
    order = find_order(visit_id, order_id)
    if order is None:
        raise KeyError(f"order {order_id} not found for visit {visit_id}")
    order["status"] = status.value
    order.update(extra)
    return order


def clear() -> None:
    # test helper — reset the in-memory store.
    _STORE.clear()
