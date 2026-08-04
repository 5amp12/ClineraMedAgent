#Checks the JSON is shaped correctly 

from pydantic import BaseModel
from typing import Optional, Any, Literal
from datetime import datetime, date

# Alias for use inside models that have a field literally named `date`. Without it the annotation
# `date: Optional[date]` resolves against the class namespace, where `date` has just been bound to
# the default (None) — pydantic then requires the field to BE None.
DateValue = date


class AdminSegment(BaseModel):
    id: int
    name: str
    title: Optional[str] = None   # null on real boards (e.g. 894, 111)

class DiagnosisTypeSegment(BaseModel):
    id: int
    code: str
    display_name: str

class MedicalFileSegment(BaseModel):
    id: int
    name: str
    url: str
    mime: str

class RecommendationSegment(BaseModel):
    id: int
    text: str
    author: str

class DiagnosticInstanceSegment(BaseModel):
    id: int
    field_values: dict[str, Any]  #May be multiple fields

class FollowupSegment(BaseModel):
    id: int
    date: Optional[DateValue] = None
    formName: Optional[str] = None
    field_values: dict[str, Any] = {}

class PatientGeneralSegement(BaseModel):
    id: int
    first_name: str
    last_name: str


class BoardSection(BaseModel):
    id: int
    title: str
    date: datetime
    # Free-form on purpose. The integration docs show "Ongoing" alongside "Completed"/"Not Started",
    # and a Literal here rejects the whole payload on an unknown status. Whether a board may be
    # processed is a policy question, already enforced by pipeline/governance_check.py.
    status: str
    admin: Optional[AdminSegment] = None

class ParticipantSection(BaseModel):
    id: int
    name: str
    email: str
    title: Optional[str] = None   # null on real boards (e.g. 166, 165, 111)

class PatientSection(BaseModel):
    id: int
    mrn: str
    name: str
    gender: str
    date_of_birth: date
    # Explicit defaults: in pydantic v2 a bare Optional[X] is required-but-nullable, so a board
    # that OMITS the key (rather than sending null) fails validation. Clinera does omit keys —
    # the docs' events array drops `patient` on one entry and `payload` on another.
    diagnosis_type: Optional[DiagnosisTypeSegment] = None
    medical_files: list[MedicalFileSegment] = []
    recommendations: Optional[list[RecommendationSegment]] = None
    diagnosticInstances: list[DiagnosticInstanceSegment] = []

    # Free-text clinical narrative. Clinera sends these on every patient, but they were absent
    # from this model, so pydantic silently dropped them and the pipeline reasoned from roughly a
    # third of the record — inferring the diagnosis from diagnosticInstances key/value pairs while
    # `summary` stated it outright, and reporting "no prior treatment given" when
    # history_present_illness described the surgery.
    summary: Optional[str] = None
    history_present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    family_history: Optional[str] = None
    genetic_testing_results: Optional[str] = None
    current_medications: Optional[str] = None
    current_symptoms_manifestations: Optional[str] = None
    current_past_clinical_trials: Optional[str] = None
    diagnosis_date: Optional[datetime] = None
    patient_status: Optional[str] = None
    followups: list[FollowupSegment] = []

    # Deliberately NOT modelled: address, mobile_number, marital_status — PHI with no bearing on
    # an MDT recommendation, and every modelled field is shipped to the LLM. Also skipped:
    # followupInstances (byte-identical duplicate of followups), extended_data /
    # patient_board_statuses / board_status / createdAt (plumbing), hcc_etiology (never populated).

class EventSection(BaseModel):
    id: int
    event_type: str
    event_timestamp: datetime
    actor_name: str
    patient: Optional[PatientGeneralSegement] = None
    payload: Optional[dict[str, Any]] = None 


class InboundVisitPayload(BaseModel):
    success: Literal[True]
    board: BoardSection
    participants: list[ParticipantSection]
    patients: list[PatientSection]
    events: list[EventSection]

    
