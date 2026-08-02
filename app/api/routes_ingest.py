#Where the API is called  --just a example set up so far--

from app.schemas.inbound import InboundVisitPayload
from fastapi import APIRouter, HTTPException
from app.services.transcript_ingest import get_board_meeting_event

router = APIRouter()

@router.get("/boards/{board_id}")
def ingest(board_id: int):  
    payload = get_board_meeting_event(board_id)

    if payload.board.status == "Not Started":
        raise HTTPException(status_code=422, detail="Board has not started; nothing to summarize yet")
    
    return payload

