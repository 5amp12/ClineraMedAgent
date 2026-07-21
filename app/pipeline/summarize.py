#Call A of the pipeline: turn a visit transcript into a structured clinical note.
#This is a LangGraph node — it takes `state` and returns only the keys it updates.

from __future__ import annotations

from typing import Any

import anthropic

# Stub until credentials are provisioned. Swap for an env lookup before going live.
client = anthropic.Anthropic(api_key="API_KEY_HERE")

MODEL = "claude-sonnet-5"

_SYSTEM = (
    "You are a clinical scribe. Extract a structured visit note from the "
    "transcript. Use only what is stated in the transcript — do not invent "
    "findings, diagnoses, or plans."
)

# The note shape the model must return. Enforced via a forced tool call so the
# response is always valid JSON with exactly these fields.
NOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason_for_visit": {
            "type": "string",
            "description": "One-line chief complaint / why the visit happened.",
        },
        "history": {
            "type": "string",
            "description": "Relevant history the patient/clinician described (HPI).",
        },
        "findings": {
            "type": "string",
            "description": "Exam findings, vitals, and results mentioned in the transcript.",
        },
        "plan": {
            "type": "string",
            "description": "Assessment and plan: diagnoses, treatment, follow-up.",
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
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        temperature=0,
        system=_SYSTEM,
        tools=[
            {
                "name": "emit_note",
                "description": "Return the structured clinical note.",
                "input_schema": NOTE_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "emit_note"},
        messages=[{"role": "user", "content": transcript_text}],
    )
    note = next(block.input for block in response.content if block.type == "tool_use")
    return {
        "note": note,
        "audit_log": state.get("audit_log", []) + ["summarize: note produced"],
    }
