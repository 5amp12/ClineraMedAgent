#CLI test surface. Pulls a real board from Clinera, runs the pipeline, prints the report.
#
#   python -m app.run_pipeline 267              # full run (calls the LLM)
#   python -m app.run_pipeline 267 --dry-run    # fetch + governance only, NO LLM calls
#   python -m app.run_pipeline 267 --out report.json
#
#Nothing is written back to Clinera.

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests
from pydantic import ValidationError

from app import config
from app.pipeline.fetch_board import fetch_board
from app.pipeline.governance_check import governance_check
from app.services import clinera_client


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _print_audit(state: dict[str, Any]) -> None:
    print("\n--- audit log ---")
    for line in state.get("audit_log", []):
        print(f"  {line}")


def dry_run(board_id: int) -> int:
    # Proves the live API works without spending a single LLM call.
    state = fetch_board({"board_id": board_id})
    state = {**state, **governance_check(state)}

    board = state.get("board", {})
    print(f"board {board.get('id')}: {board.get('title')!r} — status {board.get('status')!r}")
    print(f"participants: {len(state.get('participants', []))}  "
          f"patients: {len(state.get('patients', []))}  "
          f"events: {len(state.get('events', []))}")

    print("\n--- synthesized transcript ---")
    for segment in state.get("transcript", []):
        print(f"  {segment['speaker']}: {segment['text']}")

    _print_audit(state)

    if not state.get("governance_ok"):
        print(f"\ngovernance would HALT: {state.get('halt_reason')}")
        return 1

    print("\ngovernance passed — a full run would proceed to summarize.")
    return 0


def full_run(board_id: int, out_path: str | None) -> int:
    # Imported here, not at module scope: this pulls in app.pipeline.llm, which constructs the
    # OpenAI client. --dry-run should stay usable before that key is filled in.
    from app.pipeline.graph import build_graph

    state = build_graph().invoke({"board_id": board_id})

    _print_audit(state)

    report = state.get("report")
    if report is None:
        # governance halted, so assemble_report never ran. The audit log above says why.
        print(f"\nno report produced — gate_status {state.get('gate_status')!r}")
        return 1

    print("\n--- report ---")
    print(_dump(report))

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(_dump(report))
        print(f"\nwrote {out_path}")

    return 0


def main() -> int:
    # Audit-log lines across the pipeline contain em-dashes, and a cp1252 Windows console either
    # mangles or raises on them. Force UTF-8 so output never dies on punctuation.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="Run the visit pipeline against a live Clinera board.")
    parser.add_argument("board_id", type=int, help="Clinera board ID to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch + governance only; makes no LLM calls")
    parser.add_argument("--out", metavar="PATH", help="also write the report JSON to PATH")
    args = parser.parse_args()

    try:
        if args.dry_run:
            return dry_run(args.board_id)
        return full_run(args.board_id, args.out)
    except clinera_client.ClineraConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    except clinera_client.ClineraAuthError as e:
        print(f"auth error: {e}", file=sys.stderr)
        return 3
    except requests.HTTPError as e:
        response = e.response
        status = response.status_code if response is not None else "?"
        if status == 404:
            print(f"board {args.board_id} not found on {config.clinera_base_url()}", file=sys.stderr)
        else:
            body = response.text[:300] if response is not None else ""
            print(f"Clinera returned {status}: {body}", file=sys.stderr)
        return 4
    except ValidationError as e:
        # Schema drift — name the fields rather than dumping a wall of pydantic output.
        print(f"Clinera payload does not match InboundVisitPayload ({len(e.errors())} problems):",
              file=sys.stderr)
        for err in e.errors():
            loc = "/".join(str(p) for p in err["loc"])
            print(f"  {loc}: {err['msg']}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
