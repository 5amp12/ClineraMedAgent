#Where the API is called  --just a example set up so far--

from app.schemas.inbound import InboundVisitPayload
from fastapi import APIRouter

router = APIRouter()

@router.post("/visits/transcript")
def ingest(payload: InboundVisitPayload):  #FastAPI validates payload before this runs (schemas/inbound.py)
    return{"status": "accepted"}

