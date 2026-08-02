#The "move on" branch: turn the note + gathered FHIR data into structured proposed orders for the
#clinician to approve (README "Call B"). Feeds store_and_gate, which writes the approved orders to
#FHIR. This is a LangGraph node; it returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.llm import client, MODEL
from app.pipeline.state import PipelineState

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
    # Structured OpenAI call. Function calling is used (not strict json_schema) because each order
    # has an optional field (source).
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _context(state)},
        ],
        tools=[{"type": "function",
                "function": {"name": "recommendations", "parameters": RECOMMENDATION_SCHEMA}}],
        tool_choice={"type": "function", "function": {"name": "recommendations"}},
    )
    data = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    return data["recommendations"]


def draft_recommendations(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    recommendations = _draft(state)
    return {
        "recommendations": recommendations,
        "audit_log": audit + [f"draft_recommendations: {len(recommendations)} proposed"],
    }
