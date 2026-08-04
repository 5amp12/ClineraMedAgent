from pydantic import BaseModel
from typing import Optional, Any, Literal
from datetime import datetime, date


class ReportSegement(BaseModel):
    reason_for_visit: str
    history: str
    findings: str
    plan: str
    source_segments: list[int]

class PatientSegment(BaseModel):
    id: int
    mrn: str
    name: str
    diagnosis: str

class RecommendationSegment(BaseModel):
    id: str
    order_type: str
    details: str
    rationale: str
    source: list[str]
    confidence: float
    status: str

class SupportingDataSegment(BaseModel):
    resource: str
    # params: ?
    # data ?

class FullReportSection(BaseModel):
    id: str
    report: ReportSegement
    patient: PatientSegment
    board_id: int
    board_title: str
    transcript_id: str
    doctors_attended: list[int]
    date: date
    start_time: datetime
    end_time: datetime
    recommendations: Optional[list[RecommendationSegment]]  #Set as optional for now
    status: str
    generated_at: datetime
    generated_by: str
    provenance: list[str]
    supporting_data: Optional[list[SupportingDataSegment]]
