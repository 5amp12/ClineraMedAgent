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
    "Summarize the MEETING as a whole, never a single patient. "
    "history, findings and plan are LISTS with ONE ENTRY PER PATIENT discussed. Give every patient "
    "their own entry in each list, and set patient_name to that patient's name exactly as it "
    "appears in the record. Never merge two patients into one entry, never write 'the patient', "
    "and never leave a discussed patient out of a list. "
    "Do NOT count anything. Never state how many cases were reviewed, and never give a breakdown "
    "of how many cases of each diagnosis. Those totals are computed separately and added to the "
    "record; asked to count, you get it wrong (8 patients reported as '10 cases', a 2-prostate "
    "board reported as '5 prostate'). Name the diagnoses present without quantifying them. "
    "Use only what is stated in the record; do not invent findings, diagnoses, or plans."
)


def _per_patient(what: str) -> dict[str, Any]:
    # One entry per patient. Splitting these out of a single prose string is what lets the report
    # render (and attribute) each patient separately instead of one run-on paragraph.
    return {
        "type": "array",
        "description": f"One entry per patient discussed. {what}",
        "items": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "The patient's name exactly as written in the record.",
                },
                "text": {"type": "string", "description": what},
            },
            "required": ["patient_name", "text"],
            "additionalProperties": False,
        },
    }


# The note shape the model must return. Enforced via OpenAI structured output (strict), so the
# response is always valid JSON with exactly these fields.
NOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason_for_visit": {
            "type": "string",
            "description": "One line on why this board met and what it covered. Name the "
                           "diagnoses present; state NO counts or totals.",
        },
        "history": _per_patient("This patient's diagnosis, stage and relevant background."),
        "findings": _per_patient(
            "This patient's key results — staging, biomarkers, receptor status."
        ),
        "plan": _per_patient("The direction agreed for this patient."),
        "source_segments": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "0-based indices of the transcript segments supporting this note.",
        },
    },
    "required": ["reason_for_visit", "history", "findings", "plan", "source_segments"],
    "additionalProperties": False,
}

_SECTIONS = ("history", "findings", "plan")


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


def _normalize(name: str) -> str:
    return " ".join((name or "").split()).casefold()


def _stamp_patient_ids(note: dict[str, Any], patients: list[Any]) -> int:
    """Resolve each entry's model-written patient_name to a real Clinera patient id.

    This is weaker than draft_recommendations' attribution, which stamps patient_id from its loop
    variable so the model is never asked to attribute anything. summarize is a single board-level
    call and cannot do that without becoming per-patient minutes, so the name is matched here
    instead. An entry that fails to match keeps patient_id None and is still rendered under the
    name the model gave — dropping a patient's history would be far worse than showing it
    unlinked.
    """
    by_name = {_normalize(p.get("name")): p.get("id") for p in patients if p.get("name")}
    unmatched = 0

    for section in _SECTIONS:
        for entry in note.get(section) or []:
            if not isinstance(entry, dict):
                continue
            key = _normalize(entry.get("patient_name"))
            patient_id = by_name.get(key)

            if patient_id is None:
                # Models routinely return "Mr van Wyk" or "Hennie" for "Hennie van Wyk". Fall back
                # to an unambiguous containment match; skip it when several patients could match,
                # since a wrong id is worse than none.
                candidates = [pid for name, pid in by_name.items()
                              if key and (key in name or name in key)]
                patient_id = candidates[0] if len(candidates) == 1 else None

            entry["patient_id"] = patient_id
            if patient_id is None:
                unmatched += 1

    return unmatched


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
    unmatched = _stamp_patient_ids(note, state.get("patients") or [])

    line = f"summarize: note produced ({len(note.get('history') or [])} patient entries)"
    if unmatched:
        line += f", {unmatched} entry/entries could not be matched to a board patient"

    return {
        "note": note,
        "audit_log": state.get("audit_log", []) + [line],
    }
