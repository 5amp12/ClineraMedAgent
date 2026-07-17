#Checks the JSON is shaped correctly 

from pydantic import BaseModel
from typing import Optional, Any, Literal
from datetime import datetime, date


class AdminSegment(BaseModel):
    id: int
    name: str
    title: str

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

class PatientGeneralSegement(BaseModel):
    id: int
    first_name: str
    last_name: str


class BoardSection(BaseModel):
    id: int
    title: str
    date: datetime
    status: Literal["Completed"]
    admin: AdminSegment

class ParticipantSection(BaseModel):
    id: int
    name: str
    email: str
    title: str

class PatientSection(BaseModel):
    id: int
    mrn: str
    name: str
    gender: str
    date_of_birth: date
    diagnosis_type: DiagnosisTypeSegment
    medical_files: list[MedicalFileSegment]
    recommendations: Optional[list[RecommendationSegment]]   #Might not be optional
    diagnosticInstances: list[DiagnosticInstanceSegment]

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

    
