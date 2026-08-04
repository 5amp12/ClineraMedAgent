#Authenticated HTTP session for the Clinera AI Service API.
#
#The integration docs give two auth methods:
#  1. A long-lived service JWT sent as `Authorization: Bearer <token>`.
#  2. POST /api/auth/login with the service account email/password, which returns a SESSION COOKIE.
#
#We were handed credentials, not a token, so (2) is the live path — hence a requests.Session that
#holds the cookie rather than a bare header dict. (1) is still supported: set
#CLINERA_AI_SERVICE_TOKEN and the login step is skipped.

from __future__ import annotations

from typing import Any, Optional

import requests

from app import config

LOGIN_PATH = "/api/auth/login"
TIMEOUT = 30

_session: Optional[requests.Session] = None


class ClineraConfigError(RuntimeError):
    # Missing/invalid local configuration — the caller can't fix this by retrying.
    pass


class ClineraAuthError(RuntimeError):
    # The backend rejected our credentials.
    pass


def base_url() -> str:
    url = config.clinera_base_url()
    if not url:
        raise ClineraConfigError("CLINERA_URL must be set (see .env.example)")
    if not url.startswith("https://"):
        raise ClineraConfigError(f"CLINERA_URL must use https, got {url!r}")
    return url


def _login(session: requests.Session) -> None:
    email, password = config.clinera_email(), config.clinera_password()
    if not email or not password:
        raise ClineraConfigError(
            "Set CLINERA_AI_SERVICE_EMAIL and CLINERA_AI_SERVICE_PASSWORD, "
            "or CLINERA_AI_SERVICE_TOKEN (see .env.example)"
        )

    response = session.post(
        f"{base_url()}{LOGIN_PATH}",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        raise ClineraAuthError(
            f"login failed ({response.status_code}): {response.text[:300]}"
        )

    # The docs describe the response as "JSON + Session Cookie". requests keeps the cookie on the
    # session automatically; assert we actually got one so a silent 200-without-cookie doesn't
    # turn into a confusing 401 on the next call.
    if not session.cookies:
        raise ClineraAuthError("login returned no session cookie")


def get_session(force_login: bool = False) -> requests.Session:
    # Cached so we log in once per process rather than once per request.
    global _session

    if _session is not None and not force_login:
        return _session

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    token = config.clinera_service_token()
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    else:
        _login(session)

    _session = session
    return session


def get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET an API path (e.g. "/api/board-meeting-events/board/267") and return parsed JSON.

    Retries once through a fresh login on a 401, so an expired cookie self-heals instead of
    failing the run. Raises requests.HTTPError on any other non-2xx.
    """
    url = f"{base_url()}{path}"

    response = get_session().get(url, params=params, timeout=TIMEOUT)
    if response.status_code == 401:
        response = get_session(force_login=True).get(url, params=params, timeout=TIMEOUT)

    response.raise_for_status()
    return response.json()
