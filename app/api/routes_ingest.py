#HTTP surface. Returns the raw Clinera payload — useful for eyeballing the shape a board actually
#comes back with. Go to http://localhost:8000/docs to test.
#
#Running the pipeline is NOT exposed here: it makes three sequential LLM calls, which needs a
#job-id + polling shape rather than a synchronous request. app/run_pipeline.py is the test surface.
#
#Status policy (may this board be processed?) lives only in pipeline/governance_check.py.

from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.services import clinera_client
from app.services.transcript_ingest import get_board_meeting_event

router = APIRouter()


def _handle(exc: Exception) -> HTTPException:
    """Turn a service-layer failure into an HTTP error that says what actually went wrong.

    Without this every one of these surfaces as an opaque 500 — and schema drift is the likeliest
    failure here, so naming the offending field is the point.
    """
    if isinstance(exc, clinera_client.ClineraConfigError):
        return HTTPException(status_code=503, detail=f"Clinera not configured: {exc}")

    if isinstance(exc, clinera_client.ClineraAuthError):
        return HTTPException(status_code=502, detail=f"Clinera auth failed: {exc}")

    if isinstance(exc, ValidationError):
        fields = ["/".join(str(p) for p in err["loc"]) for err in exc.errors()]
        return HTTPException(
            status_code=422,
            detail=f"Clinera payload does not match InboundVisitPayload: {', '.join(fields)}",
        )

    if isinstance(exc, requests.HTTPError):
        response = exc.response
        status = response.status_code if response is not None else "?"
        body = response.text[:300] if response is not None else ""
        return HTTPException(status_code=502, detail=f"Clinera returned {status}: {body}")

    raise exc


@router.get("/boards/{board_id}")
def ingest(board_id: int):
    try:
        return get_board_meeting_event(board_id)
    except Exception as exc:
        raise _handle(exc) from exc
