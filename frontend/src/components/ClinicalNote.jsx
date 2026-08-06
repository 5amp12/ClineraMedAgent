import { useState } from 'react'
import {
  Stethoscope, ScrollText, Activity, ClipboardCheck, User, ClipboardList, Check, X, Loader2,
} from 'lucide-react'
import { approveOrder, rejectOrder } from '../../api/ReportCall.js'
import './ClinicalNote.css'

const sectionConfig = [
  { key: 'history', label: 'History', icon: ScrollText },
  { key: 'findings', label: 'Findings', icon: Activity },
  { key: 'plan', label: 'Plan', icon: ClipboardCheck },
]

// Anything past pending_approval is decided; the buttons stop being actionable.
const DECIDED = new Set(['approved', 'rejected', 'published', 'publish_failed'])

function formatStatus(status) {
  if (!status) return ''
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// history/findings/plan are arrays of {patient_name, text, patient_id}. Older reports stored a
// plain string; render it as a single unattributed entry rather than crashing on .map.
function toEntries(section) {
  if (!section) return []
  if (typeof section === 'string') return [{ patient_name: null, text: section }]
  return section
}

function RecommendationCard({ rec, visitId, onOrderUpdated }) {
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const decided = DECIDED.has(rec.status)

  async function decide(action) {
    setBusy(action)
    setError(null)
    try {
      const updated = action === 'approve'
        ? await approveOrder(visitId, rec.id)
        : await rejectOrder(visitId, rec.id, '')
      onOrderUpdated(updated)
    } catch (err) {
      // No optimistic update to roll back — the row only changes once the server confirms, so a
      // failed publish can't leave the UI claiming a decision that Clinera never received.
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="recommendation-item">
      <div className="recommendation-heading">
        <span className="recommendation-order-type">{rec.order_type}</span>
        <p className="recommendation-details">{rec.details}</p>
      </div>

      {rec.rationale ? <p className="recommendation-rationale">{rec.rationale}</p> : null}

      <div className="recommendation-footer">
        <span className="recommendation-status">
          {formatStatus(rec.status)}
          {typeof rec.confidence === 'number'
            ? ` · confidence ${rec.confidence.toFixed(2)}`
            : ''}
        </span>
        {decided ? null : (
          <div className="recommendation-actions">
            <button
              type="button"
              className="recommendation-btn approve"
              aria-label="Approve"
              onClick={() => decide('approve')}
              disabled={busy !== null}
            >
              {busy === 'approve' ? <Loader2 size={14} className="rec-spin" /> : <Check size={14} strokeWidth={2} />}
              Yes
            </button>
            <button
              type="button"
              className="recommendation-btn reject"
              aria-label="Reject"
              onClick={() => decide('reject')}
              disabled={busy !== null}
            >
              {busy === 'reject' ? <Loader2 size={14} className="rec-spin" /> : <X size={14} strokeWidth={2} />}
              No
            </button>
          </div>
        )}
      </div>

      {error ? <p className="recommendation-error">{error}</p> : null}
    </div>
  )
}

function ClinicalNote({ note, patients = [], recommendations = [], visitId, onOrderUpdated }) {
  // Group by patient_id, which draft_recommendations stamps from its own loop rather than asking
  // the model to attribute — the reason an order can't land under the wrong patient here.
  const ordersByPatient = new Map()
  const unassignedOrders = []
  recommendations.forEach((rec) => {
    if (rec.patient_id == null) {
      unassignedOrders.push(rec)
      return
    }
    if (!ordersByPatient.has(rec.patient_id)) ordersByPatient.set(rec.patient_id, [])
    ordersByPatient.get(rec.patient_id).push(rec)
  })

  return (
    <div className="clinical-note">
      <div className="clinical-note-banner">
        <span className="clinical-note-banner-icon">
          <Stethoscope size={18} strokeWidth={1.75} />
        </span>
        <div>
          <span className="clinical-note-banner-label">Reason for Visit</span>
          <p className="clinical-note-banner-text">{note.reason_for_visit}</p>
        </div>
      </div>

      {patients.length ? (
        <section className="patient-banner">
          <h3 className="clinical-note-section-title">
            <User size={16} strokeWidth={1.75} />
            Patients ({patients.length})
          </h3>
          <div className="patient-grid">
            {patients.map((patient) => (
              <div className="patient-card" key={patient.id ?? patient.mrn ?? patient.name}>
                <p className="clinical-note-patient-name">{patient.name}</p>
                <span className="clinical-note-patient-mrn">MRN {patient.mrn}</span>
                <span className="clinical-note-patient-diagnosis">
                  {patient.diagnosis || 'No recorded diagnosis'}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {sectionConfig.map(({ key, label, icon: Icon }) => {
        const entries = toEntries(note[key])
        return (
          <section className="clinical-note-section" key={key}>
            <h3 className="clinical-note-section-title">
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </h3>
            {entries.length === 0 ? (
              <p className="clinical-note-section-body">Nothing recorded.</p>
            ) : (
              <div className="note-entry-list">
                {entries.map((entry, i) => (
                  <div className="note-entry" key={`${entry.patient_id ?? entry.patient_name ?? i}`}>
                    {entry.patient_name ? (
                      <p className="note-entry-patient">{entry.patient_name}</p>
                    ) : null}
                    <p className="clinical-note-section-body">{entry.text}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )
      })}

      {recommendations.length > 0 ? (
        <section className="clinical-note-section">
          <h3 className="clinical-note-section-title">
            <ClipboardList size={16} strokeWidth={1.75} />
            Recommendations
          </h3>
          <p className="clinical-note-section-note">
            Proposals for clinician approval &mdash; nothing here has been actioned. Deciding an
            order publishes the board&rsquo;s summary back to Clinera.
          </p>

          {patients.map((patient) => {
            const orders = ordersByPatient.get(patient.id) || []
            if (orders.length === 0) return null
            return (
              <div className="recommendation-group" key={patient.id}>
                <p className="recommendation-group-name">{patient.name}</p>
                <div className="recommendations-list">
                  {orders.map((rec) => (
                    <RecommendationCard
                      key={rec.id}
                      rec={rec}
                      visitId={visitId}
                      onOrderUpdated={onOrderUpdated}
                    />
                  ))}
                </div>
              </div>
            )
          })}

          {unassignedOrders.length > 0 ? (
            <div className="recommendation-group">
              <p className="recommendation-group-name">Unassigned</p>
              <div className="recommendations-list">
                {unassignedOrders.map((rec) => (
                  <RecommendationCard
                    key={rec.id}
                    rec={rec}
                    visitId={visitId}
                    onOrderUpdated={onOrderUpdated}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  )
}

export default ClinicalNote
