import { useState } from 'react'
import { Stethoscope, ScrollText, Activity, ClipboardCheck, Quote, User, ClipboardList, Check, X } from 'lucide-react'
import './ClinicalNote.css'

const sectionConfig = [
  { key: 'history', label: 'History', icon: ScrollText },
  { key: 'findings', label: 'Findings', icon: Activity },
  { key: 'plan', label: 'Plan', icon: ClipboardCheck },
]

function formatStatus(status) {
  if (!status) return ''
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function ClinicalNote({ note, segments, patient, recommendations = [] }) {
  const [openSegment, setOpenSegment] = useState(null)

  const segmentByIndex = new Map(segments.map((segment) => [segment.index, segment]))

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

      {patient ? (
        <section className="patient-banner">
          <h3 className="clinical-note-section-title">
            <User size={16} strokeWidth={1.75} />
            Patient
          </h3>
          <div className="clinical-note-patient">
            <div className="clinical-note-patient-info">
              <p className="clinical-note-patient-name">{patient.name}</p>
              <span className="clinical-note-patient-mrn">MRN {patient.mrn}</span>
            </div>
          </div>
          <div className="clinical-note-patient">
            <div className="clinical-note-patient-info">
              {patient.diagnosis ? (
                <>
                <p className="clinical-note-patient-name">Diagnosis</p>
                <span className="clinical-note-patient-mrn">{patient.diagnosis}</span>
                </>
              ) : (
                <p className="clinical-note-patient-name">No previous Diagnosis</p>
              )}

            </div>
          </div>

          
        </section>
      ) : null}

      {sectionConfig.map(({ key, label, icon: Icon }) => (
        <section className="clinical-note-section" key={key}>
          <h3 className="clinical-note-section-title">
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </h3>
          <p className="clinical-note-section-body">{note[key]}</p>
        </section>
      ))}

      {recommendations.length > 0 ? (
        <section className="clinical-note-section">
          <h3 className="clinical-note-section-title">
            <ClipboardList size={16} strokeWidth={1.75} />
            Recommendations
          </h3>
          <div className="recommendations-list">
            {recommendations.map((rec) => (
              <div className="recommendation-item" key={rec.id}>
                <div className="recommendation-heading">
                  <span className="recommendation-order-type">{rec.order_type}</span>
                  <p className="recommendation-details">{rec.details}</p>
                </div>
                <div className="recommendation-footer">
                  <span className="recommendation-status">{formatStatus(rec.status)}</span>
                  <div className="recommendation-actions">
                    <button type="button" className="recommendation-btn approve" aria-label="Approve">
                      <Check size={14} strokeWidth={2} />
                      Yes
                    </button>
                    <button type="button" className="recommendation-btn reject" aria-label="Reject">
                      <X size={14} strokeWidth={2} />
                      No
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

    </div>
  )
}

export default ClinicalNote
