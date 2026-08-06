#Fetches Clinera's own board-context endpoint.
#
#Endpoint doc: GET /api/board-meeting-events/board-summary/{board_id} — "complete board context
#(board details, participants, anonymized patient list, and chronological meeting events) for AI
#processing".
#
#This is NOT our pipeline's report. It was previously validated against
#schemas/report.py:FullReportSection, which describes the report assemble_report produces
#(reason_for_visit/history/findings/plan + proposed orders). The integration guide shows this
#endpoint returning {success, board, participants, patients, events} instead, so that validation
#could only ever have raised. The name collision between the two "summaries" is the trap here.
#
#Returned unvalidated: the payload is close to InboundVisitPayload but with an anonymized,
#reduced patient shape (id/name/age/gender, no MRN or diagnostics), so neither existing model
#fits and nothing in the app consumes this yet. The pipeline reads the full board endpoint via
#transcript_ingest instead.

from __future__ import annotations

from typing import Any

from app.services import clinera_client

BOARD_SUMMARY_PATH = "/api/board-meeting-events/board-summary/{board_id}"


def get_board_summary(board_id: int) -> Any:
    return clinera_client.get_json(BOARD_SUMMARY_PATH.format(board_id=board_id))
