#Call A of the pipeline: turn the board transcript into a structured BOARD-LEVEL note.
#
#This note is display/reporting only. It is deliberately NOT fed to agent_reason or
#draft_recommendations — being written across the whole board, it skews toward whichever patient
#has the richest record, and passing it into per-patient calls leaked one patient's findings into
#another's orders. Per-patient narrative comes from agent_reason's `assessments` instead.
#
#So this node must summarize the MEETING, not a patient: how many cases, what kinds, what the
#board covered. A single-patient narrative here is wrong on a board with several patients.
#
#This is a LangGraph node — it takes `state` and returns only the keys it updates.

from __future__ import annotations

import json
from typing import Any

from app.pipeline.llm import client, MODEL

_SYSTEM = (
    "You are a clinical scribe writing the minutes of an MDT (multi-disciplinary team) board "
    "meeting. The record covers EVERY patient discussed — often several unrelated cases. "
    "Summarize the MEETING as a whole, never a single patient: say how many cases were reviewed "
    "and of what kinds, and keep per-patient detail to one clause each, always naming the "
    "patient it belongs to. Never write 'the patient' — on a multi-case board it is ambiguous "
    "and misleading. Use only what is stated in the record; do not invent findings, diagnoses, "
    "or plans."
)

# The note shape the model must return. Enforced via OpenAI structured output (strict), so the
# response is always valid JSON with exactly these fields.
NOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason_for_visit": {
            "type": "string",
            "description": "One line on why this board met and how many cases it reviewed. "
                           "Doubles as the executive overview.",
        },
        "history": {
            "type": "string",
            "description": "The case mix: each patient named, with their diagnosis and stage in "
                           "one clause. Not one patient's HPI.",
        },
        "findings": {
            "type": "string",
            "description": "Key results per patient (staging, biomarkers, receptor status), each "
                           "prefixed with the patient's name.",
        },
        "plan": {
            "type": "string",
            "description": "The direction agreed per patient, each prefixed with the patient's "
                           "name.",
        },
        "source_segments": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "0-based indices of the transcript segments supporting this note.",
        },
    },
    "required": ["reason_for_visit", "history", "findings", "plan", "source_segments"],
    "additionalProperties": False,
}


def _transcript_to_text(transcript: list[Any]) -> str:
    # Accepts either plain dicts or TranscriptSegment-like objects.
    lines = []
    for seg in transcript or []:
        if isinstance(seg, dict):
            speaker = seg.get("speaker", "unknown")
            text = seg.get("text", "")
        else:
            speaker = getattr(seg, "speaker", "unknown")
            text = getattr(seg, "text", "")
        speaker = getattr(speaker, "value", speaker)  # Enum -> its string value
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def summarize(state: dict[str, Any]) -> dict[str, Any]:
    transcript_text = _transcript_to_text(state["transcript"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": transcript_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "clinical_note", "schema": NOTE_SCHEMA, "strict": True},
        },
    )
    note = json.loads(response.choices[0].message.content)
    return {
        "note": note,
        "audit_log": state.get("audit_log", []) + ["summarize: note produced"],
    }
