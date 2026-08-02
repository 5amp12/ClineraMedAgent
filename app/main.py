#Mounts router modules
#Go to  http://localhost:8000/docs to test

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.routes_ingest import router as ingest_router

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI()

app.include_router(ingest_router, tags=["ingest"])