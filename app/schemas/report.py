from pydantic import BaseModel
from typing import Optional, Any, Literal
from datetime import datetime, date


class PatientNote(BaseModel):
    # One narrative entry belonging to one patient. patient_id is Optional because summarize
    # resolves it by matching the model's patient_name against the board's patients — an entry
    # that fails to match is kept unlinked rather than dropped (see summarize._stamp_patient_ids).
    patient_name: str
    text: str
    patient_id: Optional[int] = None

class ReportSegement(BaseModel):
    reason_for_visit: str
    # Per-patient lists, not prose. A single string collapsed a multi-patient board into one
    # run-on paragraph and left the report unable to attribute anything to a specific patient.
    history: list[PatientNote]
    findings: list[PatientNote]
    plan: list[PatientNote]
    source_segments: list[int]

class PatientSegment(BaseModel):
    id: int
    mrn: str
    name: str
    diagnosis: Optional[str] = None

class RecommendationSegment(BaseModel):
    id: str
    order_type: str
    details: str
    rationale: str
    # `source` is optional in the model's function schema, so an order can come back without it.
    source: list[str] = []
    confidence: float
    status: str
    # Stamped by draft_recommendations from its per-patient loop, never returned by the model —
    # which is what makes an order impossible to misattribute on a multi-patient board.
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None

class DoctorSegment(BaseModel):
    id: int
    name: str
    title: Optional[str] = None

class FullReportSection(BaseModel):
    id: str
    report: ReportSegement
    # The first board patient, kept for consumers that expect a single patient.
    patient: PatientSegment
    # Every patient discussed, so each recommendation's patient_id resolves from the report alone.
    patients: list[PatientSegment] = []
    board_id: int
    board_title: str
    # None on boards with no pasted transcript — Clinera exposes only an untranscribed recording.
    transcript_id: Optional[str] = None
    # Names, not bare ids: this renders as an attendee list and "6" tells a reader nothing.
    doctors_attended: list[DoctorSegment] = []
    date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    recommendations: list[RecommendationSegment] = []
    status: str
    generated_at: datetime
    generated_by: str
    provenance: list[str]
    # agent_reason's per-patient triage (key_considerations + gaps), stamped with patient_id.
    supporting_data: list[dict[str, Any]] = []
