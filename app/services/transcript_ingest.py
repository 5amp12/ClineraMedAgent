import os 
import requests

from app.schemas.inbound import InboundVisitPayload

CLINERA_BASE_URL = os.getenv("CLINERA_URL")
CLINERA_API_KEY = os.getenv("CLINERA_API_KEY")

def get_board_meeting_event(board_id: int):
    if not CLINERA_BASE_URL or not CLINERA_API_KEY:
        return RuntimeError("Clinera base url and clinera api key must be set")
    
    if not CLINERA_API_KEY.startswith("https://"):
        return RuntimeError("Clinera base url must use https")

    url = f"{CLINERA_BASE_URL}/api/board-meeting-events/board/{board_id}"
    headers = {
        "Authorization": f"Bearer {CLINERA_API_KEY}",
        "Content-Type": "application/json",
    }
    
    r = requests.get(url, headers=headers, timeout=10)

    #Checks status, raises 4** or 5**                             
    r.raise_for_status()                    
    
    #Checks payload shape, raises if wrong
    payload = InboundVisitPayload.model_validate(r.json())
         
    return payload

    