#The upstream node graph.py's header comment anticipated ("fetch_board upstream is added later").
#Pulls a board from Clinera and seeds every state key the downstream nodes read. First node in the
#graph — everything before it is just a board_id. LangGraph node; returns only the keys it updates.

from __future__ import annotations

from typing import Any

from app.pipeline.state import PipelineState
from app.services.transcript_ingest import get_board_meeting_event


# Free-text clinical fields, in the order a clinician would read them. Label -> payload key.
NARRATIVE_FIELDS: list[tuple[str, str]] = [
    ("Summary", "summary"),
    ("History of present illness", "history_present_illness"),
    ("Past medical history", "past_medical_history"),
    ("Family history", "family_history"),
    ("Genetic testing", "genetic_testing_results"),
    ("Current medications", "current_medications"),
    ("Current symptoms", "current_symptoms_manifestations"),
    ("Clinical trials", "current_past_clinical_trials"),
]


def _patient_segments(patient: dict[str, Any]) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    name = patient.get("name") or f"patient {patient.get('id')}"

    demographics = [
        f"MRN {patient['mrn']}" if patient.get("mrn") else None,
        patient.get("gender"),
        f"DOB {patient['date_of_birth']}" if patient.get("date_of_birth") else None,
    ]
    demographics = [d for d in demographics if d]
    if demographics:
        segments.append({"speaker": "board record", "text": f"{name} — {', '.join(demographics)}."})

    diagnosis = (patient.get("diagnosis_type") or {}).get("display_name")
    if diagnosis:
        diagnosed = (patient.get("diagnosis_date") or "")[:10]
        suffix = f" (diagnosed {diagnosed})" if diagnosed else ""
        segments.append({"speaker": "board record",
                         "text": f"Diagnosis for {name}: {diagnosis}{suffix}."})

    # The clinical narrative. Skip blanks and Clinera's "None."/"None" placeholders — but only as
    # whole-field values, since "None." is a real answer for current_medications and must survive
    # as such rather than being confused with a missing field.
    for label, key in NARRATIVE_FIELDS:
        value = (patient.get(key) or "").strip()
        if value:
            segments.append({"speaker": "board record", "text": f"{label} for {name}: {value}"})

    for followup in patient.get("followups") or []:
        fields = followup.get("field_values") or {}
        detail = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in fields.items())
        when = followup.get("date") or "date unknown"
        label = followup.get("formName") or "Follow-up"
        segments.append({"speaker": "board record",
                         "text": f"{label} for {name} ({when}){': ' + detail if detail else ''}."})

    for instance in patient.get("diagnosticInstances") or []:
        fields = instance.get("field_values") or {}
        if not fields:
            continue
        readable = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in fields.items())
        segments.append({"speaker": "diagnostics", "text": f"{name} — {readable}."})

    for rec in patient.get("recommendations") or []:
        text = rec.get("text")
        if text:
            # The author is a clinician, not a patient. Emitting them as the segment `speaker`
            # made the summarizer read them as a case under discussion — board 170's note named
            # the board admin "Mohamed Hassan" as a patient. Keep the patient explicit and the
            # author clearly secondary.
            author = rec.get("author") or "a board member"
            segments.append({
                "speaker": "board record",
                "text": f"Recommendation for {name} (from {author}): {text}",
            })

    return segments


def _event_segments(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    # Chronological. event_timestamp is an ISO string after mode="json", so it sorts correctly.
    segments: list[dict[str, str]] = []
    for event in sorted(events, key=lambda e: e.get("event_timestamp") or ""):
        event_type = (event.get("event_type") or "event").replace("_", " ")
        payload = event.get("payload") or {}
        detail = ", ".join(f"{k}: {v}" for k, v in payload.items())
        text = f"{event_type} ({detail})" if detail else event_type
        segments.append({"speaker": event.get("actor_name") or "system", "text": text})
    return segments


def build_transcript(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Synthesize transcript segments from the structured board payload.

    Clinera exposes no transcript endpoint — the only recorded artifact is a binary
    audio/video download. Until that is transcribed, this stands in for the real thing, in the
    {"speaker", "text"} shape summarize._transcript_to_text already accepts.
    """
    board = payload.get("board") or {}
    segments: list[dict[str, str]] = [
        {
            "speaker": "board record",
            "text": f"MDT board '{board.get('title')}' held {board.get('date')}, "
                    f"status {board.get('status')}.",
        }
    ]

    for patient in payload.get("patients") or []:
        segments.extend(_patient_segments(patient))

    segments.extend(_event_segments(payload.get("events") or []))
    return segments


def fetch_board(state: PipelineState) -> dict[str, Any]:
    audit = state.get("audit_log", [])
    board_id = state["board_id"]

    # mode="json" matters: board.date is a datetime and date_of_birth a date, but
    # assemble_report slices board date as a string ((board_date or "")[:10]) and min/max's the
    # event timestamps. Serializing to ISO strings here keeps every downstream node on primitives.
    payload = get_board_meeting_event(board_id).model_dump(mode="json")

    transcript = build_transcript(payload)

    return {
        "board": payload.get("board") or {},
        "participants": payload.get("participants") or [],
        "patients": payload.get("patients") or [],
        "events": payload.get("events") or [],
        "transcript": transcript,
        "transcript_id": None,  # no transcript source exists yet; see build_transcript
        "visit_id": f"board-{board_id}",
        # TODO: bind to a real Clinera consent field once one is exposed. Nothing in the
        # board-meeting-events payload carries consent today.
        "consent_to_process": True,
        "audit_log": audit + [
            f"fetch_board: board {board_id} fetched ({len(payload.get('patients') or [])} patients, "
            f"{len(payload.get('events') or [])} events)",
            f"fetch_board: transcript synthesized from structured board data "
            f"({len(transcript)} segments, no recording transcribed)",
        ],
    }
