#The "move on" branch: turn the note + gathered FHIR data into structured proposed orders for the
#clinician to approve (README "Call B"). Feeds store_and_gate, which writes the approved orders to
#FHIR. This is a LangGraph node; it returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.state import PipelineState

# Placeholder — wire up the real model call in _draft() below.
MODEL = "MODEL_NAME"

# Order categories. order_type maps to the FHIR resource written on approval:
#   medication -> MedicationRequest ; lab / follow_up -> ServiceRequest ; other -> (clinician review)
ORDER_TYPES = ["medication", "lab", "follow_up", "other"]

_SYSTEM = (
    "You are a clinical decision-support agent drafting proposed orders after an MDT (multi-"
    "disciplinary team) board meeting. You are given the drafted visit note, the board's "
    "structured patient diagnostics, and any clinical data retrieved from the FHIR record. "
    "Propose concrete, actionable orders (medications, labs, follow-ups) that are directly "
    "supported by that information. Do NOT invent findings or propose anything the note/data does "
    "not support. Every order is a proposal for clinician approval — never an executed action. "
    "Give each order an honest confidence between 0 and 1."
)

# The model returns an object wrapping the list of proposed orders (Anthropic tool input_schema
# must be an object at the top level). Each order follows the README ProposedOrder shape.
RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "description": "Proposed orders for clinician approval. May be empty.",
            "items": {
                "type": "object",
                "properties": {
                    "order_type": {
                        "type": "string",
                        "enum": ORDER_TYPES,
                        "description": "Category of the order.",
                    },
                    "details": {
                        "type": "string",
                        "description": "What to order, e.g. 'Metformin 500mg PO BID' or 'HbA1c'.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this is proposed, grounded in the note/fetched data.",
                    },
                    "source": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Note fields or fetched reads that support this order.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0-1 confidence that this order is appropriate.",
                    },
                },
                "required": ["order_type", "details", "rationale", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["recommendations"],
    "additionalProperties": False,
}


def _context(state: PipelineState) -> str:
    # The user-message payload the model drafts from.
    return json.dumps(
        {
            "note": state.get("note", {}),
            "patients": state.get("patients", []),
            "fetched": state.get("fetched", []),
        },
        ensure_ascii=False,
        default=str,
    )


def _draft(state: PipelineState) -> list[dict[str, Any]]:
    # PLACEHOLDER for the model call — to be written manually.
    # Given _SYSTEM + _context(state) + RECOMMENDATION_SCHEMA, call MODEL and return the list of
    # proposed orders: [{"order_type", "details", "rationale", "source", "confidence"}, ...]
    raise NotImplementedError("Wire up the MODEL_NAME call in draft_recommendations._draft()")


def draft_recommendations(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    recommendations = _draft(state)
    return {
        "recommendations": recommendations,
        "audit_log": audit + [f"draft_recommendations: {len(recommendations)} proposed"],
    }
