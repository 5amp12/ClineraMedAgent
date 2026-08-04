#Turns each patient's record + triage into structured proposed orders for clinician approval
#(README "Call B"). One model call per patient; see _context for why the scope is one patient.
#Feeds store_and_gate, which persists the orders as pending_approval.
#LangGraph node; returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.llm import client, MODEL
from app.pipeline.state import PipelineState

# Order categories, used only to classify the proposal for the reviewing clinician.
ORDER_TYPES = ["medication", "lab", "follow_up", "other"]

_SYSTEM = (
    "You are a clinical decision-support agent drafting proposed orders after an MDT (multi-"
    "disciplinary team) board meeting. You are given the complete record for a SINGLE patient and "
    "that patient's triage assessment listing key considerations and any gaps in the record. "
    "Propose concrete, actionable orders (medications, labs, follow-ups) supported directly by "
    "THIS patient's record. Every clinical fact you cite — mutations, lab values, prior "
    "procedures, appointment dates — must appear in the record given to you. Do NOT invent "
    "findings or infer them from what is typical for the diagnosis. If the record is sparse or "
    "contains placeholder text, return few orders or an empty list; that is the correct answer, "
    "not a reason to fill gaps. Every order is a proposal for clinician approval — never an "
    "executed action. Give each order an honest confidence between 0 and 1."
)

# The model returns an object wrapping the list of proposed orders — a tool's parameter schema
# must be an object at the top level. Each order follows the README ProposedOrder shape.
# patient_id/patient_name are absent by design: draft_recommendations stamps them from the loop,
# so the model is never asked to attribute an order and therefore cannot mis-attribute one.
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
                        "description": "What to order, e.g. 'Letrozole 2.5mg PO daily' or 'HbA1c'.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this is proposed, grounded in this patient's record.",
                    },
                    "source": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patient record fields that support this order.",
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


def _context(patient: dict[str, Any], assessment: dict[str, Any]) -> str:
    # ONE patient plus that same patient's triage. The board-level meeting note is excluded for
    # the reason documented in agent_reason's module header: it leaks one patient's facts into
    # another's orders.
    return json.dumps(
        {"patient": patient, "assessment": assessment},
        ensure_ascii=False,
        default=str,
    )


def _draft(patient: dict[str, Any], assessment: dict[str, Any]) -> list[dict[str, Any]]:
    # Structured OpenAI call. Function calling is used (not strict json_schema) because each order
    # has an optional field (source).
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _context(patient, assessment)},
        ],
        tools=[{"type": "function",
                "function": {"name": "recommendations", "parameters": RECOMMENDATION_SCHEMA}}],
        tool_choice={"type": "function", "function": {"name": "recommendations"}},
    )
    data = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    return data["recommendations"]


def draft_recommendations(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    patients = state.get("patients", [])

    # Assessments are keyed by patient so each draft call gets its own patient's triage and
    # nobody else's.
    by_patient = {a.get("patient_id"): a for a in state.get("assessments", [])}

    recommendations: list[dict[str, Any]] = []
    for patient in patients:
        patient_id = patient.get("id")
        assessment = by_patient.get(patient_id, {})

        for order in _draft(patient, assessment):
            # Attribution is stamped from the loop variable, NOT returned by the model. The model
            # never sees another patient's record in this call and is never asked for an id, so an
            # order cannot be assigned to the wrong patient. On a board like 170 — two patients
            # who both have bladder cancer — this is the only thing separating them.
            order["patient_id"] = patient_id
            order["patient_name"] = patient.get("name")
            recommendations.append(order)

    return {
        "recommendations": recommendations,
        "audit_log": audit + [
            f"draft_recommendations: {len(recommendations)} proposed across "
            f"{len(patients)} patients"
        ],
    }
