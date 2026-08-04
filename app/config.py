#Env/settings loader. Loads .env once on import, then hands out values through functions.
#
#The accessors below are deliberately FUNCTIONS, not module-level constants. Reading os.getenv at
#module scope binds whatever the environment happened to hold at import time, which is how the
#previous setup broke: app/main.py imported the router (and through it the service module) on the
#line ABOVE its load_dotenv() call, so the service always saw None. Reading inside a function makes
#import order irrelevant.

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# app/config.py -> app/ -> repo root
_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parent

# Repo root first, then app/, so a root .env wins. override=False means a real environment
# variable (CI, shell export) always beats the file.
for _candidate in (_REPO_ROOT / ".env", _APP_DIR / ".env"):
    if _candidate.is_file():
        load_dotenv(_candidate, override=False)


def clinera_base_url() -> str | None:
    # e.g. https://mdtv1-api.everestminds.com  (no trailing slash, no /api suffix)
    url = os.getenv("CLINERA_URL")
    return url.rstrip("/") if url else None


def clinera_email() -> str | None:
    return os.getenv("CLINERA_AI_SERVICE_EMAIL")


def clinera_password() -> str | None:
    return os.getenv("CLINERA_AI_SERVICE_PASSWORD")


def clinera_service_token() -> str | None:
    # Optional. The long-lived service JWT (auth Method 1). When absent we fall back to the
    # email/password login endpoint (Method 2), which is what the integration docs actually give us.
    return os.getenv("CLINERA_AI_SERVICE_TOKEN")
