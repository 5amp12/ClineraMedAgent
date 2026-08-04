# Clinera Frontend

React + Vite app that shows the MDT board report for a given board id at `/reports/:id`.

## Prerequisites

- Node.js (for `npm`)
- The backend API running locally — see `../app/README.md`. This app calls it directly; there is
  no mock-data mode right now.

## Running it

1. Install dependencies:
   ```
   npm install
   ```
2. Start the backend first (separate terminal, from the repo root):
   ```
   uvicorn app.main:app --reload
   ```
   It needs `app/.env` populated (`CLINERA_URL`, `CLINERA_AI_SERVICE_EMAIL`,
   `CLINERA_AI_SERVICE_PASSWORD`) or every request will fail. It listens on `http://localhost:8000`.
3. Start the frontend:
   ```
   npm run dev
   ```
   Vite serves on `http://localhost:5173` by default.
4. Visit `http://localhost:5173/reports/<board_id>`, e.g. `/reports/892`, where `<board_id>` is
   the plain numeric Clinera board id (not the `board-170`-style id you'll see inside report JSON
   — that's an internal pipeline id, unrelated to the URL).

## How data flows

`frontend/api/ReportCall.js` is the only place that talks to the backend. `report(id)`:

1. Fetches `GET http://localhost:8000/boards/{id}` — this hits our FastAPI backend, which in turn
   authenticates to Clinera and returns Clinera's raw board/participants/patients/events payload.
2. Runs that through `mapBoardToReport()` to reshape it into what the page components expect
   (`board_title`, `date`, `start_time`, `patient`, `report.{reason_for_visit,history,findings,plan}`,
   `recommendations`).

**Important:** step 2 is a plain-text stitch-together of real Clinera fields (patient summaries,
diagnoses, recommendation text) — it is *not* an AI-generated clinical note. The real pipeline that
produces an actual generated report (`app/pipeline/`) is separate, requires `OPENAI_API_KEY`, and
isn't wired to this frontend yet. If/when it is, `report()` is the only function that needs to
change.

The `API_BASE` constant in `ReportCall.js` is hardcoded to `http://localhost:8000` — there's no env
var for it yet, so pointing this at a deployed backend means editing that file directly.

Also note: the backend never hands the frontend a Clinera auth token — the AI Service credentials
stay server-side in `app/services/clinera_client.py`. Don't add direct browser → Clinera calls.

## Known gaps / things to know before touching this

- **CORS**: the backend only allows `http://localhost:5173` (see `app/main.py`). Running the
  frontend on a different port will get silently blocked by the browser.
- **No auth**: sign-in was removed (not viable yet) — there's no login, no session, anyone who can
  reach the dev server can view any board.
- **Transcript tab was removed** (it relied on `visibleChapters`, which was broken/undefined, and
  there's no real transcript data source yet anyway — see `app/README.md` on why Clinera has no
  transcript endpoint). `Reports.jsx` only renders the Report view now; `tabs` is a single-item
  array so the tab nav still renders but has nothing else to switch to.
- **Approve/Reject buttons in `ClinicalNote`** (per recommendation) are decorative — they don't
  call anything. There's no `status`/`order_type` on Clinera's raw recommendations either, so the
  status badge usually renders blank.
- **Folders nav item and Signin page were intentionally removed** — don't re-add without checking
  whether the backend/auth story has actually changed.
- `mockReport.js` / `mockClinicalNote.js` / `exampleApiReq.json` under `src/data/` are leftover
  fixtures from before the real API call was wired up. `ReportCall.js` no longer uses them.
