#Checks the JSON is shaped correctly --Currently Rough cut--

from enum import Enum
from pydantic import BaseModel

class Speaker(str, Enum):
    clinician = "clinician"
    patient = "patient"

class TranscriptSegment(BaseModel):
    speaker: Speaker
    text: str
    start: float
    end: float
    confidence: float

class InboundVisitPayload(BaseModel):
    visit_id: str
    patient_id: str
    clinician_id: str
    transcript: list[TranscriptSegment]
    consent_to_record: bool
    consent_to_process: bool
    idempotency_key: str
