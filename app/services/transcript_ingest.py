#Fetches board context from Clinera: board metadata, participants, patients (with diagnostics),
#and the chronological event log. Auth + base URL now live in clinera_client; this module owns the
#endpoint path and the payload-shape validation.
#
#Note there is no transcript endpoint on the Clinera side — the only recorded artifact is a binary
#audio/video download (/board/{id}/recording). Until that gets transcribed, the pipeline's
#transcript is synthesized from the structured data returned here (see app/pipeline/fetch_board.py).

from __future__ import annotations

from app.schemas.inbound import InboundVisitPayload
from app.services import clinera_client

BOARD_EVENTS_PATH = "/api/board-meeting-events/board/{board_id}"


def get_board_meeting_event(board_id: int) -> InboundVisitPayload:
    data = clinera_client.get_json(BOARD_EVENTS_PATH.format(board_id=board_id))

    #Checks payload shape, raises pydantic ValidationError if Clinera's shape has drifted
    return InboundVisitPayload.model_validate(data)
