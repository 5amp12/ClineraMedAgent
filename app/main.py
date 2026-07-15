#Mounts router modules
#Go to  http://localhost:8000/docs to test

from fastapi import FastAPI
from app.api.routes_ingest import router as ingest_router

app = FastAPI()

app.include_router(ingest_router, tags=["ingest"])