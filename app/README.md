# app/ — Clinical Visit Agent (production pipeline)

This package is the production system: it ingests a full meeting/visit transcript, turns it
into a structured draft note for the clinician, proposes orders (medication / lab / follow-up)
for approval, and on approval writes the corresponding FHIR resource.

It is **separate from `src/`**, which is the MedAgentBench benchmark harness (controller/worker
architecture that scores an agent against 300 fixed FHIR tasks). This package is a live service,
not an eval loop — different lifecycle, different concerns (auth, idempotency, human approval
gate, audit trail).

Status: scaffolding only. The pipeline steps that call the LLM are blocked on the inbound
transcript API key; everything else (schemas, routing, approval state machine, FHIR client
shape, sample-data tests) can be built and tested against fixtures in the meantime.

## Layout

```
app/
├── README.md                  # this file
├── main.py                    # FastAPI entrypoint, mounts the three router modules below
├── config.py                  # env/settings loader: LLM key, FHIR base URL, inbound auth secret
│
├── api/                       # HTTP layer
│   ├── routes_ingest.py       # POST endpoint that receives the transcript payload (API IN, fields 1-13)
│   ├── routes_notes.py        # GET/PATCH draft note — what doctors see (Call A output)
│   ├── routes_orders.py       # GET proposed_orders, POST /orders/{id}/approve|reject (approval gate → Call B → FHIR write)
│   └── deps.py                # auth-token/signature check + idempotency_key dedup, shared by all routes
│
├── schemas/                   # pydantic models, 1:1 with the API spec
│   ├── inbound.py              # TranscriptSegment, ConsentFlags, InboundVisitPayload
│   ├── note.py                  # DraftNote (reason_for_visit/history/findings/plan, source_segments, status, generated_by, created_at)
│   ├── orders.py                # ProposedOrder (order_type, details, rationale, source_segments, supporting_fhir_reads, agent_confidence), ApprovalDecision
│   └── fhir.py                  # MedicationRequest/ServiceRequest write payloads, requester, FhirWriteResult
│
├── pipeline/                  # the actual LLM processing — this is what plugs into the new API key
│   ├── summarize.py            # transcript[] → DraftNote  (Call A)
│   ├── extract_orders.py       # transcript[] → proposed_orders[]  (Call B)
│   └── prompts/
│       ├── summarize_note.md
│       └── extract_orders.md
│
├── services/                  # external I/O
│   ├── llm_client.py           # wraps the model call (can reuse the pattern in src/client/agents/http_agent.py)
│   ├── fhir_client.py          # GET (supporting_fhir_reads) + POST/PUT writes; extend send_get_request in src/server/tasks/medagentbench/utils.py with a POST + auth-header version
│   ├── auth.py                 # verifies inbound auth token/signature + idempotency_key
│   └── persistence.py          # stores draft notes / pending orders keyed by visit_id; tracks status: draft → pending_approval → approved/rejected → written
│
├── approval/
│   └── gate.py                 # state machine: pending_approval → clinician decision → on approve, calls fhir_client (requester = clinician_id, not the AI) → success/failure handling
│
├── tests/
│   ├── fixtures/sample_transcript.json   # synthetic transcript matching the API IN shape, for local dev before real feed arrives
│   ├── test_summarize.py
│   ├── test_extract_orders.py
│   ├── test_approval_gate.py
│   └── test_fhir_client.py
│
configs/app/
│   ├── llm.yaml                # model/version config for summarizer + order extractor (same pattern as configs/agents/*.yaml)
│   └── fhir.yaml                # FHIR base URL, auth mode
│
data/app/
│   └── sample_transcripts/     # a couple hand-written example transcripts to develop against pre-API
│
.env.example                    # LLM_API_KEY, FHIR_BASE_URL, INBOUND_AUTH_SECRET placeholders
```

## Spec-to-file map

**API IN** (transcript arrives at visit end) → `schemas/inbound.py`, received by `api/routes_ingest.py`,
authenticated/deduped via `api/deps.py` + `services/auth.py`.

**API OUT — Call A** (store draft note, fires after summarization) → produced by
`pipeline/summarize.py`, shaped by `schemas/note.py`, persisted via `services/persistence.py`,
exposed to doctors via `api/routes_notes.py`.

**API OUT — Call B** (proposed orders, surfaced to approval gate) → produced by
`pipeline/extract_orders.py`, shaped by `schemas/orders.py`, exposed/decided via
`api/routes_orders.py` and `approval/gate.py`.

**On approval → FHIR write** (MedicationRequest / ServiceRequest, requester = clinician) →
`approval/gate.py` calls `services/fhir_client.py`, result shaped by `schemas/fhir.py`.

## What's blocked on the API key vs. what isn't

Blocked: `pipeline/summarize.py`, `pipeline/extract_orders.py`, `services/llm_client.py` — these
need the real transcript feed / model endpoint to be meaningful.

Not blocked, buildable now: `schemas/*`, `api/*` routing skeletons, `approval/gate.py` state
machine, `services/fhir_client.py` shape (against the existing Docker FHIR server used by the
benchmark), `services/persistence.py`, and all of `tests/` against fixture data in
`data/app/sample_transcripts/`.
