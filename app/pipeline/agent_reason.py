#The reasoning step (ReAct). Looks at the note + patient diagnostics + anything fetched so far
#and decides: pull MORE clinical data from the FHIR record (-> clinera_get), or move on
#(-> draft_recommendations). This is a LangGraph node; it returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.state import PipelineState

# Placeholder — wire up the real model call in _decide() below.
MODEL = "MODEL_NAME"

# How many FHIR fetches we allow before forcing the pipeline to move on. Guards the
# clinera_get -> agent_reason loop against spinning forever.
MAX_FETCHES = 3

# FHIR resources agent_reason is allowed to request. Taken from the resources the repo
# already knows about (data/medagentbench/funcs_v1.json).
FHIR_RESOURCES = ["Condition", "Observation", "MedicationRequest", "Procedure", "Patient"]

_SYSTEM = (
    "You are a clinical decision-support agent reviewing the output of an MDT (multi-"
    "disciplinary team) board meeting. You are given the drafted visit note, the board's "
    "structured patient diagnostics, and any clinical data already retrieved from the FHIR "
    "record. Decide whether you have enough information to safely draft recommendations, or "
    "whether you must first retrieve additional clinical data (labs, conditions, active "
    "medications, procedures). Only request data that is genuinely missing and material to the "
    "recommendation. When in doubt and nothing material is missing, proceed."
)

# The decision shape the model must return. resource/params are only meaningful when
# action == "fetch".
DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["fetch", "proceed"],
            "description": "'fetch' to retrieve more FHIR data, 'proceed' to move on to drafting.",
        },
        "resource": {
            "type": "string",
            "enum": FHIR_RESOURCES,
            "description": "Which FHIR resource to read. Required when action is 'fetch'.",
        },
        "params": {
            "type": "object",
            "description": "FHIR query params, e.g. {\"patient\": \"119\", \"code\": \"HbA1c\"}.",
            "additionalProperties": {"type": "string"},
        },
        "rationale": {
            "type": "string",
            "description": "One line explaining the decision.",
        },
    },
    "required": ["action", "rationale"],
    "additionalProperties": False,
}


def _context(state: PipelineState) -> str:
    # The user-message payload the model reasons over.
    return json.dumps(
        {
            "note": state.get("note", {}),
            "patients": state.get("patients", []),
            "already_fetched": state.get("fetched", []),
        },
        ensure_ascii=False,
        default=str,
    )


def _decide(state: PipelineState) -> dict[str, Any]:
    # PLACEHOLDER for the model call — to be written manually.
    # Given _SYSTEM + _context(state) + DECISION_SCHEMA, call MODEL and return a decision dict:
    #   {"action": "fetch"|"proceed", "resource"?: str, "params"?: dict, "rationale": str}
    raise NotImplementedError("Wire up the MODEL_NAME call in agent_reason._decide()")


def agent_reason(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    fetch_count = state.get("fetch_count", 0)

    # Cap short-circuit: once we've fetched enough, force progress WITHOUT calling the model.
    # (Also keeps this path runnable before the model call is wired up.)
    if fetch_count >= MAX_FETCHES:
        return {
            "decision": "proceed",
            "audit_log": audit + [f"agent_reason: fetch cap ({MAX_FETCHES}) reached -> proceed"],
        }

    decision = _decide(state)
    action = decision["action"]
    update: dict[str, Any] = {
        "decision": action,
        "audit_log": audit + [f"agent_reason: {action} — {decision.get('rationale', '')}"],
    }
    if action == "fetch":
        update["fetch_request"] = {
            "resource": decision.get("resource"),
            "params": decision.get("params", {}),
        }
    return update


def route_after_reason(state: PipelineState) -> str:
    # Conditional edge: which node runs next after agent_reason.
    return "clinera_get" if state.get("decision") == "fetch" else "draft_recommendations"
