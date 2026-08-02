#Mock FHIR write client. Maps an approved order to a FHIR resource and "writes" it.
#MOCK: there is no real FHIR endpoint yet — this returns a canned success. Replace write_order's
#body with a real authed POST later (extend the send_get_request pattern in
#src/server/tasks/medagentbench/utils.py with a POST + auth header).

from __future__ import annotations

import uuid
from typing import Any, Optional

# order_type -> FHIR resource written on approval.
RESOURCE_FOR: dict[str, Optional[str]] = {
    "medication": "MedicationRequest",
    "lab": "ServiceRequest",
    "follow_up": "ServiceRequest",
    "other": None,  # no auto-write; clinician handles it manually
}


def write_order(order: dict[str, Any], requester: str) -> dict[str, Any]:
    resource = RESOURCE_FOR.get(order.get("order_type"))
    if resource is None:
        return {"ok": False, "reason": f"order_type '{order.get('order_type')}' has no FHIR mapping"}

    # --- MOCK: swap for a real POST {fhir_base}/{resource} once an endpoint exists. ---
    payload = {
        "resourceType": resource,
        "status": "active",
        # requester is the approving clinician — never the AI.
        "requester": {"reference": f"Practitioner/{requester}"},
        "text": order.get("details"),
    }
    return {
        "ok": True,
        "resource_type": resource,
        "resource_id": f"mock-{uuid.uuid4().hex[:8]}",
        "payload": payload,
    }
