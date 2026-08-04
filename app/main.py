#Mounts router modules
#Go to  http://localhost:8000/docs to test

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Imported first and for its side effect: app.config loads .env at import time. It used to be a
# load_dotenv() call below the router import, which ran too late — the service module had already
# read os.getenv at import and cached None.
from app import config  # noqa: F401
from app.api.routes_ingest import router as ingest_router

app = FastAPI()

# Vite dev server runs on a different origin than this API; without this the browser blocks
# ReportCall.js's fetch() before it even reaches the route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(ingest_router, tags=["ingest"])