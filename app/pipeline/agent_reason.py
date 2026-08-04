#The reasoning step. Produces a clinical triage assessment PER PATIENT, which
#draft_recommendations then drafts from.
#
#One model call per patient, each seeing ONLY that patient's record — no other patient, and not
#the board-level meeting note. Two reasons, both learned the hard way on board 170 (two patients
#who both have bladder cancer):
#  * A single call covering every patient produces text that cannot be tied back to one of them,
#    and quietly spends its whole answer on whichever record is richest — one patient got skipped.
#  * The meeting note is written across the whole board and skews to the richest record, so
#    passing it in leaked one patient's facts into another's output (Final Test's FGFR3 mutation
#    and February follow-up showed up in Tiger Welch's orders; he has neither).
#Scoping each call to one patient means attribution comes from the loop, not the model's judgment.
#
#This node used to run a ReAct fetch/proceed loop against a FHIR record. There is no FHIR backend:
#the Clinera spec exposes one board-context call returning the complete record up front, so there
#was nothing to iteratively retrieve — the loop just recycled canned data into invented findings.
#
#LangGraph node; returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.llm import client, MODEL
from app.pipeline.state import PipelineState

_SYSTEM = (
    "You are a clinical decision-support agent reviewing one patient's case from an MDT (multi-"
    "disciplinary team) board meeting. You are given the complete record for a SINGLE patient — "
    "history, diagnostics, genetics, current medications and symptoms. Assess what the board is "
    "deciding for this patient, and state plainly what the record does NOT tell you. Do not "
    "invent findings, results, or medications: if something material is missing, name it as a "
    "gap rather than assuming a value. A sparse or placeholder-looking record is itself a "
    "finding — report it as gaps rather than filling it in."
)

# Triage output. `gaps` is deliberately part of the contract: the previous design expressed missing
# information by fetching it, and with no source to fetch from, unmet needs must stay visible
# rather than being silently filled in by the model.
ASSESSMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "key_considerations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The clinical decisions this board is making, one per entry.",
        },
        "gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Material information absent from the record. Empty if nothing is missing.",
        },
        "rationale": {
            "type": "string",
            "description": "One line summarizing the overall clinical picture.",
        },
    },
    "required": ["key_considerations", "gaps", "rationale"],
    "additionalProperties": False,
}


def _context(patient: dict[str, Any]) -> str:
    # ONE patient record and nothing else — see the module header for why the board-level
    # meeting note is excluded.
    return json.dumps({"patient": patient}, ensure_ascii=False, default=str)


def _assess(patient: dict[str, Any]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _context(patient)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "assessment", "schema": ASSESSMENT_SCHEMA, "strict": True},
        },
    )
    return json.loads(response.choices[0].message.content)


def agent_reason(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    patients = state.get("patients", [])

    assessments: list[dict[str, Any]] = []
    for patient in patients:
        assessment = _assess(patient)
        # patient_id/patient_name are stamped here, from the loop — never returned by the model,
        # which is why they cannot be mis-attributed.
        assessments.append({
            "patient_id": patient.get("id"),
            "patient_name": patient.get("name"),
            **assessment,
        })

    total_gaps = sum(len(a.get("gaps", [])) for a in assessments)
    return {
        "assessments": assessments,
        "audit_log": audit + [
            f"agent_reason: assessed {len(assessments)} patients individually "
            f"({total_gaps} gaps total)"
        ],
    }
