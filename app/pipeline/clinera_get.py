#Mock FHIR read node. agent_reason routes here when it needs more clinical data; this returns a
#canned response and loops back to agent_reason. This is a LangGraph node — returns only the keys
#it updates.
#
#MOCK: there is no real Clinera FHIR spec yet (the only contract we have is the board-meeting-
#events endpoint, implemented in app/services/transcript_ingest.py). Once a FHIR base URL exists,
#replace the MOCK_FHIR lookup below with a real GET — see send_get_request() in
#src/server/tasks/medagentbench/utils.py for the request/response shape to reuse.

from __future__ import annotations

from typing import Any

from app.pipeline.state import PipelineState

# One canned FHIR-ish bundle per resource type agent_reason can request.
MOCK_FHIR: dict[str, dict[str, Any]] = {
    "Condition": {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Condition", "code": {"text": "Bladder cancer"}, "clinicalStatus": "active"}}
        ],
    },
    "Observation": {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Observation", "code": {"text": "HbA1c"}, "valueQuantity": {"value": 7.1, "unit": "%"}}}
        ],
    },
    "MedicationRequest": {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "MedicationRequest", "medicationCodeableConcept": {"text": "Metformin 500mg"}, "status": "active"}}
        ],
    },
    "Procedure": {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Procedure", "code": {"text": "Cystoscopy"}, "status": "completed"}}
        ],
    },
    "Patient": {
        "resourceType": "Patient",
        "id": "example",
        "name": [{"text": "Lysandra Hobbs"}],
        "gender": "female",
    },
}


def clinera_get(state: PipelineState) -> dict[str, Any]:
    request = state.get("fetch_request") or {}
    resource = request.get("resource")
    params = request.get("params", {})
    audit = state.get("audit_log", [])

    # --- MOCK: swap this lookup for a real FHIR GET once a base URL is available. ---
    data = MOCK_FHIR.get(resource, {"resourceType": "Bundle", "entry": []})

    return {
        "fetched": state.get("fetched", []) + [{"resource": resource, "params": params, "data": data}],
        "fetch_count": state.get("fetch_count", 0) + 1,
        "fetch_request": None,  # consumed
        "audit_log": audit + [f"clinera_get: fetched {resource} (mock)"],
    }
