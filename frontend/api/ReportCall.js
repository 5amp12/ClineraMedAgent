// Calls our own backend, never Clinera directly — the AI_SERVICE_TOKEN Clinera requires lives
// server-side (app/services/clinera_client.py) and must never end up in browser-shipped JS.
const API_BASE = "http://localhost:8000"

// /boards/{id} returns Clinera's raw board/patients/events shape, not the reason_for_visit/
// history/findings/plan "report" shape ClinicalNote.jsx renders (that only exists once the LLM
// pipeline runs). This stitches a readable note together from the raw fields so the frontend
// has something real to show in the meantime — same field names Reports.jsx already reads.
function joinPerPatient(patients, pick) {
    return patients
        .map((patient) => {
            const value = pick(patient)
            return value ? `${patient.name}: ${value}` : null
        })
        .filter(Boolean)
        .join('; ')
}

function mapBoardToReport(raw) {
    const board = raw.board || {}
    const patients = raw.patients || []
    const primaryPatient = patients[0] || {}

    const diagnoses = [...new Set(patients.map((p) => p.diagnosis_type?.display_name).filter(Boolean))]

    return {
        board_title: board.title,
        date: board.date,
        start_time: board.date,
        patient: {
            name: primaryPatient.name,
            mrn: primaryPatient.mrn,
            diagnosis: primaryPatient.diagnosis_type?.display_name,
        },
        report: {
            reason_for_visit: diagnoses.length
                ? `MDT board meeting to discuss ${diagnoses.join(', ')} cases presented.`
                : board.title,
            history: joinPerPatient(patients, (p) => p.summary || p.history_present_illness || p.past_medical_history),
            findings: joinPerPatient(patients, (p) => p.diagnosis_type?.display_name),
            plan: joinPerPatient(patients, (p) => (p.recommendations || []).map((r) => r.text).join(' ')),
        },
        recommendations: patients.flatMap((p) =>
            (p.recommendations || []).map((rec) => ({
                id: rec.id,
                order_type: rec.author,
                details: rec.text,
                status: null,
            })),
        ),
    }
}

export async function report(id) {
    const response = await fetch(`${API_BASE}/boards/${id}`)

    if (!response.ok) {
        const detail = await response.text()
        throw new Error(`Failed to load report for board ${id}: ${response.status} ${detail}`)
    }

    const raw = await response.json()
    return mapBoardToReport(raw)
}