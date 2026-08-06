// Calls our own backend, never Clinera directly — the AI_SERVICE_TOKEN Clinera requires lives
// server-side (app/services/clinera_client.py) and must never end up in browser-shipped JS.
const API_BASE = "http://localhost:8000"

// FastAPI puts the useful message in `detail`; falling back to the raw body keeps us honest when
// the failure came from somewhere else (a proxy, a CORS block) and there is no JSON at all.
async function failure(response, what) {
    let detail
    try {
        const body = await response.json()
        detail = body.detail || JSON.stringify(body)
    } catch {
        detail = await response.text()
    }
    return new Error(`${what} (${response.status}): ${detail}`)
}

async function request(path, options) {
    const response = await fetch(`${API_BASE}${path}`, options)
    if (!response.ok) {
        throw await failure(response, `Request to ${path} failed`)
    }
    return response.json()
}

function postJson(path, body) {
    return request(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body ?? {}),
    })
}

/**
 * Poll target for one visit. Returns the run envelope, NOT a bare report:
 *   { run_status: 'running' }                     — still working, poll again
 *   { run_status: 'ready',  report: {...} }       — done
 *   { run_status: 'failed', error: '...' }        — the run raised
 *   { run_status: 'halted', halt_reason: '...' }  — governance refused the board
 *
 * The envelope exists because the report has its own `status` field (the approval gate status),
 * so run state could not share that key.
 */
export function report(visitId) {
    return request(`/reports/${encodeURIComponent(visitId)}`)
}

/** Every past run, newest first, for the landing page list. */
export function listReports() {
    return request('/reports')
}

/**
 * Kick off a pipeline run for a Clinera board. `transcript` is optional — without it the pipeline
 * synthesizes one from the structured board record. Returns { visit_id, run_status } immediately;
 * a full board is ~17 sequential model calls, so the caller polls report() from there.
 */
export function runBoard(boardId, transcript) {
    return postJson(`/boards/${encodeURIComponent(boardId)}/run`, { transcript: transcript || null })
}

/** Approve one proposed order. Resolves to the updated order. */
export function approveOrder(visitId, orderId) {
    return postJson(
        `/visits/${encodeURIComponent(visitId)}/orders/${encodeURIComponent(orderId)}/approve`,
    )
}

/** Reject one proposed order. Rejections are published to Clinera too — see approval/gate.py. */
export function rejectOrder(visitId, orderId, reason) {
    return postJson(
        `/visits/${encodeURIComponent(visitId)}/orders/${encodeURIComponent(orderId)}/reject`,
        { reason: reason || '' },
    )
}
