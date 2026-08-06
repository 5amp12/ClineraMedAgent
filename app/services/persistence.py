#SQLite store for draft notes + proposed orders, keyed by visit_id. Tracks each order's status
#through the approval lifecycle.
#
#This was a module-level dict, which meant a record only existed inside the process that created
#it: a pipeline run in the CLI left nothing for the API server to approve, and a uvicorn reload
#wiped every pending order. Since approval publishes the board summary to Clinera, the record has
#to outlive the run that produced it.
#
#One row per visit, the whole record as a JSON blob — the shape is nested and always read whole,
#so columns would buy nothing. The function surface is unchanged; nothing outside this file cares.

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class OrderStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    published = "published"            # board summary pushed to Clinera
    publish_failed = "publish_failed"  # decision stands; the push to Clinera did not land


class RunStatus(str, Enum):
    # Lifecycle of one pipeline run, so the API can answer "is it done?" without holding the
    # request open for ~17 sequential LLM calls.
    running = "running"
    ready = "ready"
    halted = "halted"    # governance_check refused the board; halt_reason says why
    failed = "failed"    # the run raised; error carries the message


# Override with CLINERA_DB_PATH; ":memory:" restores the old ephemeral behaviour for tests.
DB_PATH = os.getenv("CLINERA_DB_PATH") or str(Path(__file__).resolve().parents[2] / "clinera.db")

_local = threading.local()


def _conn() -> sqlite3.Connection:
    # One connection per thread: sqlite3 connections are not safe to share across threads, and
    # FastAPI serves sync endpoints on a thread pool.
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS visits ("
                     "visit_id TEXT PRIMARY KEY, record TEXT NOT NULL)")
        # Run status lives in SQLite for the same reason the visit record does: the run happens on
        # a background thread (or the CLI), and a module-level dict would not survive a uvicorn
        # reload — leaving the UI polling a run nobody is tracking any more.
        conn.execute("CREATE TABLE IF NOT EXISTS runs ("
                     "visit_id TEXT PRIMARY KEY, board_id INTEGER, status TEXT NOT NULL, "
                     "error TEXT, started_at TEXT, finished_at TEXT)")
        conn.commit()
        _local.conn = conn
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(visit_id: str) -> Optional[dict[str, Any]]:
    row = _conn().execute("SELECT record FROM visits WHERE visit_id = ?", (visit_id,)).fetchone()
    return json.loads(row[0]) if row else None


def _write(visit_id: str, record: dict[str, Any]) -> None:
    conn = _conn()
    conn.execute("INSERT INTO visits (visit_id, record) VALUES (?, ?) "
                 "ON CONFLICT(visit_id) DO UPDATE SET record = excluded.record",
                 (visit_id, json.dumps(record, default=str)))
    conn.commit()


def save_pending(visit_id: str, note: dict[str, Any],
                 recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    orders = [
        {**rec, "id": f"{visit_id}-ord-{i}", "status": OrderStatus.pending_approval.value}
        for i, rec in enumerate(recommendations, start=1)
    ]
    record = {"visit_id": visit_id, "note": note, "orders": orders, "created_at": _now()}
    _write(visit_id, record)
    return record


def get(visit_id: str) -> Optional[dict[str, Any]]:
    return _read(visit_id)


def find_order(visit_id: str, order_id: str) -> Optional[dict[str, Any]]:
    # Returns a COPY, unlike the old dict store which handed back a live reference. Mutating the
    # result does nothing; go through set_order_status to persist a change.
    record = _read(visit_id)
    if not record:
        return None
    return next((o for o in record["orders"] if o["id"] == order_id), None)


def list_pending() -> list[dict[str, Any]]:
    records = [json.loads(r[0]) for r in _conn().execute("SELECT record FROM visits")]
    return [
        r for r in records
        if any(o["status"] == OrderStatus.pending_approval.value for o in r["orders"])
    ]


def set_order_status(visit_id: str, order_id: str, status: OrderStatus,
                     **extra: Any) -> dict[str, Any]:
    record = _read(visit_id)
    order = None
    if record:
        order = next((o for o in record["orders"] if o["id"] == order_id), None)
    if order is None:
        raise KeyError(f"order {order_id} not found for visit {visit_id}")

    order["status"] = status.value
    order.update(extra)
    _write(visit_id, record)
    return order


def attach_report(visit_id: str, report: dict[str, Any]) -> None:
    # Store the assembled report on the record, so a visit's note + orders + report live together.
    record = _read(visit_id)
    if record is not None:
        record["report"] = report
        _write(visit_id, record)


def start_run(visit_id: str, board_id: int) -> dict[str, Any]:
    # Upsert: re-running a board replaces the previous run's status rather than accumulating rows,
    # matching the 1-to-1 visit_id -> record relationship in `visits`.
    conn = _conn()
    conn.execute(
        "INSERT INTO runs (visit_id, board_id, status, error, started_at, finished_at) "
        "VALUES (?, ?, ?, NULL, ?, NULL) "
        "ON CONFLICT(visit_id) DO UPDATE SET board_id = excluded.board_id, "
        "status = excluded.status, error = NULL, started_at = excluded.started_at, "
        "finished_at = NULL",
        (visit_id, board_id, RunStatus.running.value, _now()),
    )
    conn.commit()
    return get_run(visit_id)


def finish_run(visit_id: str, status: RunStatus, error: str | None = None) -> dict[str, Any]:
    conn = _conn()
    conn.execute(
        "UPDATE runs SET status = ?, error = ?, finished_at = ? WHERE visit_id = ?",
        (status.value, error, _now(), visit_id),
    )
    conn.commit()
    return get_run(visit_id)


def _run_row(row: Any) -> dict[str, Any]:
    visit_id, board_id, status, error, started_at, finished_at = row
    return {
        "visit_id": visit_id,
        "board_id": board_id,
        "status": status,
        "error": error,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def get_run(visit_id: str) -> Optional[dict[str, Any]]:
    row = _conn().execute(
        "SELECT visit_id, board_id, status, error, started_at, finished_at "
        "FROM runs WHERE visit_id = ?",
        (visit_id,),
    ).fetchone()
    return _run_row(row) if row else None


def list_runs() -> list[dict[str, Any]]:
    """Every run, newest first, each enriched with enough of its record to render a list row.

    The landing page needs a board title and counts next to each entry; reading the stored record
    here keeps that join in one place rather than making the route stitch two sources together.
    """
    rows = _conn().execute(
        "SELECT visit_id, board_id, status, error, started_at, finished_at "
        "FROM runs ORDER BY started_at DESC"
    ).fetchall()

    runs = []
    for row in rows:
        run = _run_row(row)
        record = _read(run["visit_id"]) or {}
        report = record.get("report") or {}
        orders = record.get("orders") or []
        run.update({
            "board_title": report.get("board_title"),
            "date": report.get("date"),
            "patient_count": len(report.get("patients") or []),
            "order_count": len(orders),
            "pending_count": sum(
                1 for o in orders if o.get("status") == OrderStatus.pending_approval.value
            ),
        })
        runs.append(run)
    return runs


def clear() -> None:
    # test helper — drop every stored visit.
    conn = _conn()
    conn.execute("DELETE FROM visits")
    conn.execute("DELETE FROM runs")
    conn.commit()
