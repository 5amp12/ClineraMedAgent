#Mounts router modules
#Go to  http://localhost:8000/docs to test

from fastapi import FastAPI

# Imported first and for its side effect: app.config loads .env at import time. It used to be a
# load_dotenv() call below the router import, which ran too late — the service module had already
# read os.getenv at import and cached None.
from app import config  # noqa: F401
from app.api.routes_ingest import router as ingest_router

app = FastAPI()

app.include_router(ingest_router, tags=["ingest"])