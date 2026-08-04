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


def clear() -> None:
    # test helper — drop every stored visit.
    conn = _conn()
    conn.execute("DELETE FROM visits")
    conn.commit()
