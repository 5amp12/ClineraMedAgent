#Fetches the AI-facing board summary from Clinera: the generated report (reason_for_visit/
#history/findings/plan), patient, and recommendation data used to render the Reports page.
#
#Endpoint doc: GET /api/board-meeting-events/board-summary/{board_id} — "complete board context
#... for AI processing". Response shape matches schemas/report.py:FullReportSection.

from __future__ import annotations

from app.schemas.report import FullReportSection
from app.services import clinera_client

BOARD_SUMMARY_PATH = "/api/board-meeting-events/board-summary/{board_id}"


def get_board_summary(board_id: int) -> FullReportSection:
    data = clinera_client.get_json(BOARD_SUMMARY_PATH.format(board_id=board_id))

    #Checks payload shape, raises pydantic ValidationError if Clinera's shape has drifted
    return FullReportSection.model_validate(data)
