#Mounts router modules
#Go to  http://localhost:8000/docs to test

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Imported first and for its side effect: app.config loads .env at import time. It used to be a
# load_dotenv() call below the router import, which ran too late — the service module had already
# read os.getenv at import and cached None.
from app import config  # noqa: F401
from app.api.routes_ingest import router as ingest_router
from app.api.routes_reports import router as reports_router

app = FastAPI()

# Vite dev server runs on a different origin than this API; without this the browser blocks
# ReportCall.js's fetch() before it even reaches the route. POST is required for starting a run
# and for approving/rejecting an order — with GET alone the browser blocks the preflight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(ingest_router, tags=["ingest"])
app.include_router(reports_router, tags=["reports"])